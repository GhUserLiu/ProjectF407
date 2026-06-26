/**
 * @file timing.h
 * @brief 高精度时间测量（基于 DWT 周期计数器）
 *
 * 用 STM32F407 的 DWT->CYCCNT（32 位自由运行周期计数器）做 µs 级墙钟测量。
 * 不依赖 TIM2/HAL。µs 换算依赖 SystemCoreClock 在 Timing_Init 前已被
 * SystemClock_Config() 设为真实主频（168MHz）。
 */
#ifndef TIMING_H
#define TIMING_H

#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 单次测量结果 */
typedef struct {
    uint32_t start_count;       /* 起始周期数（DWT_CYCCNT） */
    uint32_t end_count;         /* 结束周期数 */
    uint32_t elapsed_cycles;    /* 经过周期数（uint32 回绕安全） */
    uint32_t elapsed_us;        /* 经过微秒（=cycles/clock_mhz） */
    float    elapsed_ms;        /* 经过毫秒 */
} TimingResult_t;

/* 多次测量统计 */
typedef struct {
    uint32_t min_us;
    uint32_t max_us;
    uint32_t total_us;
    uint32_t count;
    float mean_us;
    float mean_ms;
} TimingStats_t;

/* 性能标记集合（特征提取 / 模型推理 / 端到端） */
typedef struct {
    TimingResult_t feature_extract;
    TimingStats_t  feature_stats;
    TimingResult_t model_inference;
    TimingStats_t  model_stats;
    TimingResult_t total_time;
    TimingStats_t  total_stats;
    uint32_t measurement_count;
} PerformanceMarkers_t;

/* ---- 基础 ---- */
bool     Timing_Init(void);                        /* 使能 DWT，记录 clock_mhz */
uint32_t Timing_GetMicroseconds(void);             /* 当前 µs 时间戳 */
void     Timing_DelayUs(uint32_t us);
void     Timing_DelayMs(uint32_t ms);
uint32_t Timing_GetClockMHz(void);                 /* 返回 clock_mhz（用于报告） */

/* ---- 单次区间 ---- */
void Timing_Start(TimingResult_t *r);
void Timing_Stop(TimingResult_t *r);

/* ---- 统计 ---- */
void Timing_InitStats(TimingStats_t *s);
void Timing_AddSample(TimingStats_t *s, uint32_t elapsed_us);
void Timing_CalculateStats(TimingStats_t *s);

/* ---- 性能标记 ---- */
void Timing_InitPerformanceMarkers(PerformanceMarkers_t *m);
void Timing_StartFeatureExtract(PerformanceMarkers_t *m);
void Timing_StopFeatureExtract(PerformanceMarkers_t *m);
void Timing_StartModelInference(PerformanceMarkers_t *m);
void Timing_StopModelInference(PerformanceMarkers_t *m);
void Timing_StartTotal(PerformanceMarkers_t *m);
void Timing_StopTotal(PerformanceMarkers_t *m);

#ifdef __cplusplus
}
#endif
#endif /* TIMING_H */
