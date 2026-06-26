/**
 * @file model_weights.c
 * @brief INT8 线性 SVM 参数（train_svm.py 导出，const 链入 FLASH）
 * w_q: 17 int8  | threshold: int32  | sx/sw/b/A/B: 校准元数据(float)
 */
#include "model.h"

const int8_t  g_svm_wq[MODEL_INPUT_DIM] = { 11, 2, 0, 0, 0, 0, 0, 0, 0, -113, 127, 46, 0, 0, 0, 0, 0 };
const int32_t g_svm_threshold = 0;
const float   g_svm_sx[MODEL_INPUT_DIM] = { 8.63753637e+00f, 2.95179875e+00f, 3.68640172e-02f, 5.87850439e-01f, 7.87743397e-02f, 2.09471038e-02f, 1.97293338e+00f, 8.11548206e-01f, 4.82879081e-02f, 4.91602476e+01f, 3.21267471e+01f, 1.93355725e+01f, 3.62296295e-03f, 2.73464866e-03f, 1.96192868e-03f, 1.50809221e-03f, 1.27368867e-03f };
const float   g_svm_sw = 1.84142353e-04f;
const float   g_svm_b  = 2.62427966e-07f;
const float   g_svm_platt_A = 4.16743679e+00f;
const float   g_svm_platt_B = -7.74052607e-01f;

/* 权重已作为 const 链入 FLASH；此函数保留 API 连续性，恒返回 true */
bool Model_LoadPretrainedWeights(void) { return true; }
