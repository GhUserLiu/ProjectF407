/**
 * @file features.h
 * @brief CAN 总线 17 维特征提取（适用于 STM32F407）。
 *
 * 说明：
 *  - 熵（can_id_entropy / payload_entropy）单位为【nats】（自然对数）。最大值为
 *    ln(k)（k 个非空桶）。训练侧（train_model.py）须用 np.log 与之一致。
 *  - 窗口为【tumbling 窗口】：Features_ResetWindow 直接清零计数（不滑动）。
 *  - Features_Extract 使用文件级 static 缓冲，非重入；运行期仅 CAN_RxMessage_Handler
 *    / 基准测试单实例调用，不会并发。
 */
#ifndef FEATURES_H
#define FEATURES_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

#define CAN_WINDOW_SIZE      100      /* 窗口大小（CAN 消息数量） */
#define FEATURE_DIM          17       /* 特征维度 */
#define MAX_CAN_ID           0x1FFF   /* 最大 11 位 CAN ID */
#define MAX_DLC              8        /* 最大数据长度码 */

typedef struct {
    uint32_t can_id;
    uint8_t  dlc;
    uint8_t  data[8];
    uint32_t timestamp;               /* 微秒 */
} CANMessage_t;

typedef struct {
    CANMessage_t messages[CAN_WINDOW_SIZE];
    uint16_t      count;
    uint32_t      start_time;
} CANWindow_t;

typedef struct {
    /* CAN ID 特征 (4) */
    float can_id_mean;
    float can_id_std;
    float can_id_entropy;            /* nats */
    float can_id_unique;
    /* DLC 特征 (2) */
    float dlc_mean;
    float dlc_std;
    /* 载荷特征 (3) */
    float payload_mean;
    float payload_std;
    float payload_entropy;           /* nats */
    /* 时间间隔特征 (3) */
    float interval_mean;
    float interval_std;
    float frequency;
    /* Top 5 ID 频率 (5) */
    float top1_freq;
    float top2_freq;
    float top3_freq;
    float top4_freq;
    float top5_freq;
} Features_t;

void Features_InitWindow(CANWindow_t *window);
bool Features_AddMessage(CANWindow_t *window, const CANMessage_t *msg);
void Features_Extract(const CANWindow_t *window, Features_t *features);
float Features_Mean(const float *data, uint16_t len);
float Features_Std(const float *data, uint16_t len, float mean);
float Features_Entropy(const uint16_t *counts, uint16_t len, uint32_t total);
void Features_ToArray(const Features_t *features, float *output);
void Features_ResetWindow(CANWindow_t *window);

#ifdef __cplusplus
}
#endif
#endif /* FEATURES_H */
