/**
 * @file model.c
 * @brief INT8 线性 SVM 推理实现。
 *
 * 核心分类全程整型：int8 权重 × int8 输入 → int32 点积 → 与整数阈值比较。
 * 权重 g_svm_* 为 const（model_weights.c），链入 FLASH，0 字节 RAM。
 */
#include "model.h"
#include "model_weights.h"   /* g_svm_wq / g_svm_threshold / g_svm_sx / ... */
#include <math.h>

static int32_t clamp_i32(int32_t v, int32_t lo, int32_t hi)
{
    return (v < lo) ? lo : (v > hi ? hi : v);
}

bool Model_Init(void)
{
    return true;   /* 参数为 const 已链入；无需运行期初始化 */
}

void Model_Predict(const float *input, ModelResult_t *result)
{
    int32_t dot = 0;
    float margin;
    float p;
    int i;

    if (input == NULL || result == NULL) return;

    /* 输入量化 → int8，与 int8 权重做 int32 点积 */
    for (i = 0; i < MODEL_INPUT_DIM; i++) {
        int32_t xq = (int32_t)lroundf(input[i] / g_svm_sx[i]);
        xq = clamp_i32(xq, -128, 127);
        dot += (int32_t)g_svm_wq[i] * xq;
    }

    result->score           = dot;
    result->is_attack       = (dot >= g_svm_threshold);
    result->predicted_class = result->is_attack ? 1u : 0u;

    /* 反量化 margin + Platt 概率（仅用于报告，不影响整型决策） */
    margin = g_svm_sw * (float)dot + g_svm_b;
    p = 1.0f / (1.0f + expf(-(g_svm_platt_A * margin + g_svm_platt_B)));
    result->attack_probability  = p;
    result->normal_probability  = 1.0f - p;
}
