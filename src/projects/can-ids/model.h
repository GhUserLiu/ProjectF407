/**
 * @file model.h
 * @brief INT8 线性 SVM 推理（CAN 入侵检测，二分类）。
 *
 * 决策 f(x)=w·x+b，攻击 ⟺ f>=0。INT8 全整型核心：
 *   x_q[i] = clamp(round(x[i]/s_x[i]), -128, 127)
 *   dot    = Σ w_q[i] * x_q[i]   (int32)
 *   攻击   ⟺ dot >= threshold    (threshold = round(-b/s_w)，已折叠 scale)
 * 边缘浮点（校准元数据）：输入量化(17 次 ÷) 与 Platt 概率(1 次 expf)。
 * 权重参数为 const（见 model_weights.h），链入 FLASH，不占 RAM。
 */
#ifndef MODEL_H
#define MODEL_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MODEL_INPUT_DIM 17

typedef struct {
    uint8_t  predicted_class;     /* 0=正常, 1=攻击 */
    float    attack_probability;  /* Platt 校准 */
    float    normal_probability;
    bool     is_attack;
    int32_t  score;               /* 原始 int32 点积，便于核验 */
} ModelResult_t;

bool Model_Init(void);
void Model_Predict(const float *input, ModelResult_t *result);

#ifdef __cplusplus
}
#endif
#endif /* MODEL_H */
