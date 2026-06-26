/**
 * @file model_weights.h
 * @brief INT8 线性 SVM 参数声明
 */
#ifndef MODEL_WEIGHTS_H
#define MODEL_WEIGHTS_H
#include "model.h"
#include <stdbool.h>

extern const int8_t  g_svm_wq[MODEL_INPUT_DIM];
extern const int32_t g_svm_threshold;
extern const float   g_svm_sx[MODEL_INPUT_DIM];
extern const float   g_svm_sw;
extern const float   g_svm_b;
extern const float   g_svm_platt_A;
extern const float   g_svm_platt_B;

bool Model_LoadPretrainedWeights(void);

#endif /* MODEL_WEIGHTS_H */
