/**
 * @file timing.c
 * @brief DWT 周期计数器实现的真实 µs 时间测量。
 *
 * 替换原版被 mock（恒定 100µs）的 TIM2 实现。直接操作 DWT 寄存器，
 * 不依赖仓库 timer.c（后者用到未定义的 TIM_TypeDef/HAL_TIM_*，编译不过）。
 */
#include "timing.h"
#include <stddef.h>

/* DWT / CoreDebug 寄存器（裸地址） */
#define DWT_CYCCNT_ADDR   0xE0001004u
#define DWT_CONTROL_ADDR  0xE0001000u
#define DEMCR_ADDR        0xE000EDFCu

#define DWT_CYCCNT   (*(volatile uint32_t *)DWT_CYCCNT_ADDR)
#define DWT_CONTROL  (*(volatile uint32_t *)DWT_CONTROL_ADDR)
#define DEMCR        (*(volatile uint32_t *)DEMCR_ADDR)

#define DEMCR_TRCENA     (1u << 24)
#define DWT_CYCCNTENA    (1u << 0)

/* SystemCoreClock 由 stm32f4xx_hal_ext.c 定义，SystemClock_Config 会设为 168MHz */
extern uint32_t SystemCoreClock;

static uint32_t s_clock_mhz = 0u;

bool Timing_Init(void)
{
    DEMCR |= DEMCR_TRCENA;          /* 使能 trace（DWT 计数前提） */
    DWT_CYCCNT = 0u;                /* 复位计数器 */
    DWT_CONTROL |= DWT_CYCCNTENA;   /* 使能 CYCCNT */

    s_clock_mhz = SystemCoreClock / 1000000u;
    if (s_clock_mhz == 0u) {
        s_clock_mhz = 168u;         /* 兜底，避免除零 */
    }
    return true;
}

uint32_t Timing_GetClockMHz(void) { return s_clock_mhz; }

uint32_t Timing_GetMicroseconds(void)
{
    return DWT_CYCCNT / s_clock_mhz;
}

void Timing_DelayUs(uint32_t us)
{
    uint32_t start = DWT_CYCCNT;
    uint32_t ticks = us * s_clock_mhz;
    while ((DWT_CYCCNT - start) < ticks) { /* 回绕安全 */ }
}

void Timing_DelayMs(uint32_t ms)
{
    while (ms--) {
        Timing_DelayUs(1000u);
    }
}

void Timing_Start(TimingResult_t *r)
{
    if (r == NULL) return;
    r->start_count = DWT_CYCCNT;
}

void Timing_Stop(TimingResult_t *r)
{
    if (r == NULL) return;
    r->end_count = DWT_CYCCNT;
    r->elapsed_cycles = r->end_count - r->start_count;          /* uint32 回绕安全 */
    r->elapsed_us     = (s_clock_mhz > 0u) ? (r->elapsed_cycles / s_clock_mhz) : 0u;
    r->elapsed_ms     = (float)r->elapsed_us / 1000.0f;
}

void Timing_InitStats(TimingStats_t *s)
{
    if (s == NULL) return;
    s->min_us = 0xFFFFFFFFu;
    s->max_us = 0u;
    s->total_us = 0u;
    s->count = 0u;
    s->mean_us = 0.0f;
    s->mean_ms = 0.0f;
}

void Timing_AddSample(TimingStats_t *s, uint32_t elapsed_us)
{
    if (s == NULL) return;
    if (elapsed_us < s->min_us) s->min_us = elapsed_us;
    if (elapsed_us > s->max_us) s->max_us = elapsed_us;
    s->total_us += elapsed_us;
    s->count++;
}

void Timing_CalculateStats(TimingStats_t *s)
{
    if (s == NULL || s->count == 0u) return;
    s->mean_us = (float)s->total_us / (float)s->count;
    s->mean_ms = s->mean_us / 1000.0f;
}

void Timing_InitPerformanceMarkers(PerformanceMarkers_t *m)
{
    if (m == NULL) return;
    Timing_InitStats(&m->feature_stats);
    Timing_InitStats(&m->model_stats);
    Timing_InitStats(&m->total_stats);
    m->measurement_count = 0u;
}

void Timing_StartFeatureExtract(PerformanceMarkers_t *m) { if (m) Timing_Start(&m->feature_extract); }
void Timing_StopFeatureExtract(PerformanceMarkers_t *m)  { if (!m) return; Timing_Stop(&m->feature_extract);  Timing_AddSample(&m->feature_stats, m->feature_extract.elapsed_us); }

void Timing_StartModelInference(PerformanceMarkers_t *m) { if (m) Timing_Start(&m->model_inference); }
void Timing_StopModelInference(PerformanceMarkers_t *m)  { if (!m) return; Timing_Stop(&m->model_inference); Timing_AddSample(&m->model_stats, m->model_inference.elapsed_us); }

void Timing_StartTotal(PerformanceMarkers_t *m) { if (m) Timing_Start(&m->total_time); }
void Timing_StopTotal(PerformanceMarkers_t *m)  { if (!m) return; Timing_Stop(&m->total_time); Timing_AddSample(&m->total_stats, m->total_time.elapsed_us); m->measurement_count++; }
