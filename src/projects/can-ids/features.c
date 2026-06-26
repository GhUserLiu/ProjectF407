/**
 * @file features.c
 * @brief CAN 17 维特征提取实现。
 *
 * 相对原版的改动：
 *  - 大缓冲由栈(auto, ~5.9KB) 改为文件级 static，消除 1KB 栈溢出风险（非重入，见头注释）。
 *  - 时间间隔差加单调保护：ts[i]<ts[i-1] 时丢弃该样本，避免 uint32 回绕污染均值/方差/频率。
 *  - 删除第一段错误的唯一 ID 计数（死代码），仅保留正确的第二段并把 memset 紧贴其前。
 *  - 移除 fast_sqrt（直接 sqrtf），保留 fast_log。
 */
#include "features.h"
#include <string.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif
#define MAXF(a, b) ((a) > (b) ? (a) : (b))

/* ===== 文件级静态缓冲（非重入；避免栈爆炸） ===== */
static float    s_can_ids[CAN_WINDOW_SIZE];
static float    s_dlcs[CAN_WINDOW_SIZE];
static float    s_intervals[CAN_WINDOW_SIZE - 1];
static float    s_payload_bytes[CAN_WINDOW_SIZE * MAX_DLC];   /* 最多 800 */
static uint16_t s_id_counts[CAN_WINDOW_SIZE];
static uint32_t s_can_id_values[CAN_WINDOW_SIZE];
static uint8_t  s_byte_counts[256];
static uint16_t s_nonzero_counts[256];

static float fast_log(float x)
{
    if (x <= 0.0f) return 0.0f;
    return logf(x);
}

void Features_InitWindow(CANWindow_t *window)
{
    if (window == NULL) return;
    memset(window, 0, sizeof(CANWindow_t));
}

bool Features_AddMessage(CANWindow_t *window, const CANMessage_t *msg)
{
    if (window == NULL || msg == NULL) return false;
    if (window->count >= CAN_WINDOW_SIZE) return true;     /* 窗口已满 */
    window->messages[window->count] = *msg;
    window->count++;
    if (window->count == 1) {
        window->start_time = msg->timestamp;
    }
    return (window->count >= CAN_WINDOW_SIZE);
}

void Features_ResetWindow(CANWindow_t *window)
{
    /* tumbling 窗口：直接清零（非滑动）。滑动需 memmove 末尾 (WINDOW-stride) 条。 */
    if (window == NULL) return;
    window->count = 0;
    window->start_time = 0;
}

float Features_Mean(const float *data, uint16_t len)
{
    float sum = 0.0f;
    uint16_t i;
    if (data == NULL || len == 0) return 0.0f;
    for (i = 0; i < len; i++) sum += data[i];
    return sum / (float)len;
}

float Features_Std(const float *data, uint16_t len, float mean)
{
    float sum_sq = 0.0f;
    uint16_t i;
    if (data == NULL || len == 0) return 0.0f;
    for (i = 0; i < len; i++) {
        float diff = data[i] - mean;
        sum_sq += diff * diff;
    }
    return sqrtf(sum_sq / (float)len);          /* 总体标准差（ddof=0），须与训练侧一致 */
}

float Features_Entropy(const uint16_t *counts, uint16_t len, uint32_t total)
{
    float entropy = 0.0f;
    uint16_t i;
    if (counts == NULL || len == 0 || total == 0) return 0.0f;
    for (i = 0; i < len; i++) {
        if (counts[i] > 0) {
            float prob = (float)counts[i] / (float)total;
            entropy -= prob * fast_log(prob);  /* nats */
        }
    }
    return entropy;
}

void Features_Extract(const CANWindow_t *window, Features_t *features)
{
    const uint16_t n = window->count;
    uint16_t unique_count = 0;
    uint16_t interval_count = 0;
    uint16_t payload_count = 0;
    uint16_t i, j;
    uint16_t nonzero_len = 0;
    uint8_t  dlc;

    if (window == NULL || features == NULL || n == 0) return;

    /* ========== CAN ID 统计 ========== */
    for (i = 0; i < n; i++) {
        s_can_ids[i] = (float)window->messages[i].can_id;
    }
    features->can_id_mean = Features_Mean(s_can_ids, n);
    features->can_id_std  = Features_Std(s_can_ids, n, features->can_id_mean);

    /* 唯一 ID + 频率（单次扫描，正确版本） */
    memset(s_id_counts, 0, sizeof(s_id_counts));
    unique_count = 0;
    for (i = 0; i < n; i++) {
        bool found = false;
        for (j = 0; j < unique_count; j++) {
            if (window->messages[i].can_id == s_can_id_values[j]) {
                s_id_counts[j]++;
                found = true;
                break;
            }
        }
        if (!found) {
            s_can_id_values[unique_count] = window->messages[i].can_id;
            s_id_counts[unique_count] = 1;
            unique_count++;
        }
    }
    features->can_id_unique  = (float)unique_count;
    features->can_id_entropy = Features_Entropy(s_id_counts, unique_count, n);

    /* ========== DLC 统计 ========== */
    for (i = 0; i < n; i++) {
        s_dlcs[i] = (float)window->messages[i].dlc;
    }
    features->dlc_mean = Features_Mean(s_dlcs, n);
    features->dlc_std  = Features_Std(s_dlcs, n, features->dlc_mean);

    /* ========== 载荷统计 ========== */
    memset(s_byte_counts, 0, sizeof(s_byte_counts));
    payload_count = 0;
    for (i = 0; i < n; i++) {
        dlc = window->messages[i].dlc;
        if (dlc > MAX_DLC) dlc = MAX_DLC;
        for (j = 0; j < dlc; j++) {
            uint8_t b = window->messages[i].data[j];
            s_payload_bytes[payload_count] = (float)b;
            s_byte_counts[b]++;
            payload_count++;
        }
    }
    if (payload_count > 0) {
        features->payload_mean    = Features_Mean(s_payload_bytes, payload_count);
        features->payload_std     = Features_Std(s_payload_bytes, payload_count, features->payload_mean);
        nonzero_len = 0;
        for (i = 0; i < 256u; i++) {
            if (s_byte_counts[i] > 0) {
                s_nonzero_counts[nonzero_len++] = s_byte_counts[i];
            }
        }
        features->payload_entropy = Features_Entropy(s_nonzero_counts, nonzero_len, payload_count);
    } else {
        features->payload_mean = 0.0f;
        features->payload_std = 0.0f;
        features->payload_entropy = 0.0f;
    }

    /* ========== 时间间隔统计（单调保护） ========== */
    interval_count = 0;
    for (i = 1; i < n; i++) {
        uint32_t prev = window->messages[i - 1].timestamp;
        uint32_t cur  = window->messages[i].timestamp;
        if (cur >= prev) {                       /* 防御非单调时间戳回绕 */
            s_intervals[interval_count++] = (float)(cur - prev);
        }
    }
    if (interval_count > 0) {
        features->interval_mean = Features_Mean(s_intervals, interval_count);
        features->interval_std  = Features_Std(s_intervals, interval_count, features->interval_mean);
        features->frequency = (features->interval_mean > 0.0f)
                            ? (1000000.0f / features->interval_mean)   /* Hz（µs→s） */
                            : 0.0f;
    } else {
        features->interval_mean = 0.0f;
        features->interval_std = 0.0f;
        features->frequency = 0.0f;
    }

    /* ========== Top 5 ID 频率（插入排序） ========== */
    {
        float    top_freqs[5] = {0};
        uint32_t top_ids[5]   = {0};
        uint8_t  k;
        for (i = 0; i < unique_count; i++) {
            float freq = (float)s_id_counts[i] / (float)n;
            for (j = 0; j < 5u; j++) {
                if (freq > top_freqs[j]) {
                    for (k = 4; k > j; k--) {
                        top_freqs[k] = top_freqs[k - 1];
                        top_ids[k]   = top_ids[k - 1];
                    }
                    top_freqs[j] = freq;
                    top_ids[j]   = s_can_id_values[i];
                    break;
                }
            }
        }
        features->top1_freq = top_freqs[0];
        features->top2_freq = top_freqs[1];
        features->top3_freq = top_freqs[2];
        features->top4_freq = top_freqs[3];
        features->top5_freq = top_freqs[4];
        (void)top_ids;   /* 仅 freq 进入特征向量；ids 留作调试 */
    }
}

void Features_ToArray(const Features_t *features, float *output)
{
    if (features == NULL || output == NULL) return;
    output[0]  = features->can_id_mean;
    output[1]  = features->can_id_std;
    output[2]  = features->can_id_entropy;
    output[3]  = features->can_id_unique;
    output[4]  = features->dlc_mean;
    output[5]  = features->dlc_std;
    output[6]  = features->payload_mean;
    output[7]  = features->payload_std;
    output[8]  = features->payload_entropy;
    output[9]  = features->interval_mean;
    output[10] = features->interval_std;
    output[11] = features->frequency;
    output[12] = features->top1_freq;
    output[13] = features->top2_freq;
    output[14] = features->top3_freq;
    output[15] = features->top4_freq;
    output[16] = features->top5_freq;
}
