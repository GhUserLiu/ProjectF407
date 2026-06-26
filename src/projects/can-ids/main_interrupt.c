/**
 ******************************************************************************
 * @file    : main_interrupt.c
 * @brief   : CAN 入侵检测系统 - STM32F407 主程序（计时优先验证）
 *
 * 含：内嵌启动（向量表 + Reset_Handler）、真实 168MHz 时钟、DWT µs 计时、
 * USART1 printf 输出、LED 心跳、特征提取/推理/端到端三项基准测试与统计报告。
 * 命名为 main_interrupt.c 让 Makefile 自动链入 stm32f4xx_hal_ext.c。
 ******************************************************************************
 */
#include <stdint.h>
#include <stdio.h>

#include "stm32f4xx_hal.h"
#include "board.h"
#include "config.h"
#include "timing.h"
#include "uart_retarget.h"
#include "model.h"
#include "model_weights.h"
#include "features.h"

/* ========== 链接脚本符号 ========== */
extern uint32_t _estack;
extern uint32_t _sidata, _sdata, _edata;
extern uint32_t _sbss, _ebss;
extern uint32_t SystemCoreClock;   /* stm32f4xx_hal_ext.c 定义 */

/* ========== 窗口 / 统计（全局，避免栈占用） ========== */
/* SVM 参数为 const 链入 FLASH（model_weights.c），不占 RAM */
static CANWindow_t          g_can_window;
static PerformanceMarkers_t g_perf_markers;
static uint32_t g_normal_count = 0;
static uint32_t g_attack_count = 0;
static uint32_t g_total_processed = 0;

/* ========== 裸寄存器（简化版 HAL 未提供这些外设类型） ========== */
#define RCC_BASE_ADDR      0x40023800u
#define FLASH_BASE_ADDR    0x40023C00u
#define PWR_BASE_ADDR      0x40007000u
#define GPIOF_BASE_ADDR    0x40021400u

#define RCC_CR       (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x00u))
#define RCC_PLLCFGR  (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x04u))
#define RCC_CFGR     (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x08u))
#define RCC_AHB1ENR  (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x30u))
#define RCC_APB1ENR  (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x40u))
#define FLASH_ACR    (*(volatile uint32_t *)(FLASH_BASE_ADDR + 0x00u))
#define PWR_CR       (*(volatile uint32_t *)(PWR_BASE_ADDR + 0x00u))
#define GPIOF_MODER  (*(volatile uint32_t *)(GPIOF_BASE_ADDR + 0x00u))
#define GPIOF_ODR    (*(volatile uint32_t *)(GPIOF_BASE_ADDR + 0x14u))

#define RCC_CR_HSERDY        (1u << 17)
#define RCC_CR_HSEON         (1u << 16)
#define RCC_CR_PLLON         (1u << 24)
#define RCC_CR_PLLRDY        (1u << 25)
#define RCC_CFGR_SW_PLL      0x2u
#define RCC_CFGR_SWS_MSK     0xCu
#define RCC_CFGR_SWS_PLL     (0x2u << 2)

/* ========== 异常处理前向声明（SysTick_Handler 由 stm32f4xx_hal.c 提供） ========== */
void Reset_Handler(void);
void NMI_Handler(void);
void HardFault_Handler(void);
void MemManage_Handler(void);
void BusFault_Handler(void);
void UsageFault_Handler(void);
void SVC_Handler(void);
void DebugMon_Handler(void);
void PendSV_Handler(void);
extern void SysTick_Handler(void);

/* ============================================================================
 * 真实 168MHz 时钟（裸寄存器）
 * ============================================================================ */
static void SystemClock_Config(void)
{
    volatile uint32_t timeout;
    uint32_t pllm;
    uint32_t pllsrc;

    /* 1. PWR 时钟 + VOS scale1（F407 168MHz 无需 overdrive） */
    RCC_APB1ENR |= (1u << 28);
    PWR_CR |= (1u << 15);
    for (timeout = 0xFFFFu; timeout; timeout--) { }

    /* 2. FLASH：5 WS + 预取 + I/D-Cache（必须在升频前） */
    FLASH_ACR = 5u | (1u << 8) | (1u << 9) | (1u << 10);

    /* 3. 切回 HSI 并关 PLL */
    RCC_CFGR = 0x00000000u;
    RCC_CR  &= ~RCC_CR_PLLON;
    for (timeout = 0xFFFFu; timeout && (RCC_CR & RCC_CR_PLLRDY); timeout--) { }

    /* 4. 总线分频：AHB /1, APB1 /4(42MHz), APB2 /2(84MHz) */
    RCC_CFGR = (0x0u << 4) | (0x5u << 8) | (0x4u << 11);

    /* 5. HSE 优先（8MHz），超时回退 HSI（16MHz）；均 PLL→168MHz */
    RCC_CR |= RCC_CR_HSEON;
    for (timeout = 0x40000u; timeout && !(RCC_CR & RCC_CR_HSERDY); timeout--) { }
    if (RCC_CR & RCC_CR_HSERDY) {
        pllm   = HSE_FREQ_HZ / 1000000u;
        pllsrc = (1u << 22);
    } else {
        pllm   = HSI_FREQ_HZ / 1000000u;
        pllsrc = 0u;
    }

    /* 6. PLLCFGR: PLLM, PLLN=336, PLLP=2, PLLQ=7, src */
    RCC_PLLCFGR = pllm
                | (336u << 6)
                | (((2u >> 1) - 1u) << 16)
                | (7u << 24)
                | pllsrc;

    /* 7. 开 PLL 并等就绪 */
    RCC_CR |= RCC_CR_PLLON;
    for (timeout = 0x40000u; timeout && !(RCC_CR & RCC_CR_PLLRDY); timeout--) { }

    /* 8. 切系统时钟到 PLL */
    RCC_CFGR = (RCC_CFGR & ~0x3u) | RCC_CFGR_SW_PLL;
    for (timeout = 0x40000u; timeout && ((RCC_CFGR & RCC_CFGR_SWS_MSK) != RCC_CFGR_SWS_PLL); timeout--) { }

    /* 9. 更新 SystemCoreClock + 重配 SysTick（HAL_Init 把它配成了 16MHz） */
    SystemCoreClock = SYSCLK_FREQ_168M;
    HAL_SYSTICK_Config(SystemCoreClock / 1000u);
}

static void LED_Init(void)
{
    RCC_AHB1ENR |= (1u << 5);                 /* GPIOF */
    GPIOF_MODER &= ~(0x3u << 18); GPIOF_MODER |= (0x1u << 18);  /* PF9 */
    GPIOF_MODER &= ~(0x3u << 20); GPIOF_MODER |= (0x1u << 20);  /* PF10 */
    GPIOF_ODR   |= (1u << 9) | (1u << 10);    /* 灭 */
}

/* ============================================================================
 * 测试数据与基准
 * ============================================================================ */
static void GenerateTestMessage(CANMessage_t *msg, uint32_t index)
{
    uint8_t i;
    if (msg == NULL) return;
    msg->can_id = 0x100u + (index % 16u);
    msg->dlc = (uint8_t)(4u + (index % 5u));
    for (i = 0; i < msg->dlc; i++) {
        msg->data[i] = (uint8_t)((index * 7u + i * 3u) % 256u);
    }
    msg->timestamp = index * 1000u;           /* 1ms 间隔，单调递增 */
}

static void RunFeatureExtractionTest(void)
{
    Features_t features;
    float feature_array[FEATURE_DIM];
    uint16_t i;
    uint32_t t;

    for (i = 0; i < CAN_WINDOW_SIZE; i++) {
        CANMessage_t msg;
        GenerateTestMessage(&msg, i);
        Features_AddMessage(&g_can_window, &msg);
    }
    for (t = 0; t < TEST_ITERATIONS; t++) {
        Timing_StartFeatureExtract(&g_perf_markers);
        Features_Extract(&g_can_window, &features);
        Features_ToArray(&features, feature_array);
        Timing_StopFeatureExtract(&g_perf_markers);
    }
    Timing_CalculateStats(&g_perf_markers.feature_stats);
    printf("  单次特征提取: %lu us (unique=%.0f entropy=%.3f)\n",
           (unsigned long)g_perf_markers.feature_extract.elapsed_us,
           features.can_id_unique, features.can_id_entropy);
}

static void RunInferenceTest(void)
{
    float test_input[MODEL_INPUT_DIM];
    ModelResult_t result;
    uint8_t i;
    uint32_t t;

    for (i = 0; i < MODEL_INPUT_DIM; i++) {
        test_input[i] = (float)i * 0.1f;
    }
    for (t = 0; t < TEST_ITERATIONS; t++) {
        Timing_StartModelInference(&g_perf_markers);
        Model_Predict(test_input, &result);
        Timing_StopModelInference(&g_perf_markers);
        if (result.is_attack) { g_attack_count++; } else { g_normal_count++; }
    }
    Timing_CalculateStats(&g_perf_markers.model_stats);
    printf("  单次推理: %lu us (正常=%.4f 攻击=%.4f score=%ld -> %s)\n",
           (unsigned long)g_perf_markers.model_inference.elapsed_us,
           result.normal_probability, result.attack_probability,
           (long)result.score, result.is_attack ? "攻击" : "正常");
}

static void RunEndToEndTest(void)
{
    Features_t features;
    float feature_array[FEATURE_DIM];
    ModelResult_t result;
    uint32_t iter;
    uint16_t i;

    for (iter = 0; iter < TEST_ITERATIONS; iter++) {
        Features_ResetWindow(&g_can_window);
        for (i = 0; i < CAN_WINDOW_SIZE; i++) {
            CANMessage_t msg;
            GenerateTestMessage(&msg, i);
            Features_AddMessage(&g_can_window, &msg);
        }
        Timing_StartTotal(&g_perf_markers);
        Features_Extract(&g_can_window, &features);
        Features_ToArray(&features, feature_array);
        Model_Predict(feature_array, &result);
        Timing_StopTotal(&g_perf_markers);
        g_total_processed++;
    }
    Timing_CalculateStats(&g_perf_markers.total_stats);
}

static void PrintStatistics(void)
{
    float mean_total_us = g_perf_markers.total_stats.mean_us;
    float windows_per_sec  = (mean_total_us > 0.0f) ? (1000000.0f / mean_total_us) : 0.0f;
    float messages_per_sec = windows_per_sec * (float)CAN_WINDOW_SIZE;

    printf("\n========== 最终测量报告（%lu 次迭代） ==========\n",
           (unsigned long)TEST_ITERATIONS);

    printf("【特征提取】 avg=%.2f us  min=%lu  max=%lu\n",
           g_perf_markers.feature_stats.mean_us,
           (unsigned long)g_perf_markers.feature_stats.min_us,
           (unsigned long)g_perf_markers.feature_stats.max_us);
    printf("【模型推理】 avg=%.2f us  min=%lu  max=%lu\n",
           g_perf_markers.model_stats.mean_us,
           (unsigned long)g_perf_markers.model_stats.min_us,
           (unsigned long)g_perf_markers.model_stats.max_us);
    printf("【端到端  】 avg=%.2f us  min=%lu  max=%lu\n",
           g_perf_markers.total_stats.mean_us,
           (unsigned long)g_perf_markers.total_stats.min_us,
           (unsigned long)g_perf_markers.total_stats.max_us);

    printf("【处理能力】\n");
    printf("  窗口处理速率: %.2f 窗口/秒\n", windows_per_sec);
    printf("  消息处理速率: %.0f 消息/秒 (= 窗口率 x %d)\n",
           messages_per_sec, CAN_WINDOW_SIZE);

    printf("【分类统计】 正常=%lu  攻击=%lu  端到端处理=%lu\n",
           (unsigned long)g_normal_count, (unsigned long)g_attack_count,
           (unsigned long)g_total_processed);
    printf("==============================================\n");
}

/* ============================================================================
 * CAN 接收回调（运行期集成点；暂以 GenerateTestMessage 之外的逻辑保留）
 * ============================================================================ */
void CAN_RxMessage_Handler(const CANMessage_t *msg)
{
    bool window_full = Features_AddMessage(&g_can_window, msg);
    if (window_full) {
        Features_t features;
        float feature_array[FEATURE_DIM];
        ModelResult_t result;

        Features_Extract(&g_can_window, &features);
        Features_ToArray(&features, feature_array);
        Model_Predict(feature_array, &result);

        if (result.is_attack) {
            /* 检测到攻击：触发警报（翻转 LED1 + 上报） */
            BOARD_LED_TOGGLE(BOARD_LED1);
            printf("[ALERT] 疑似攻击  can_id=0x%lX  p=%.3f\n",
                   (unsigned long)msg->can_id, result.attack_probability);
        }
        Features_ResetWindow(&g_can_window);
    }
}

/* ============================================================================
 * 主函数
 * ============================================================================ */
int main(void)
{
    TimingResult_t probe;

    HAL_Init();
    SystemClock_Config();
    Timing_Init();
    USART1_Init_Direct(UART_BAUDRATE);
    LED_Init();

    printf("\n==========================================\n");
    printf("CAN 入侵检测系统 - STM32F407\n");
    printf("==========================================\n");
    printf("SystemCoreClock = %lu Hz (clock_mhz=%lu)\n",
           (unsigned long)SystemCoreClock, (unsigned long)Timing_GetClockMHz());
    printf("模型: INT8 线性 SVM (%d 维特征, w_q=%dB int8 + 整数阈值)\n",
           MODEL_INPUT_DIM, MODEL_INPUT_DIM);

    /* SVM 参数为 const 已链入 FLASH；这里仅作可用性确认 */
    Model_Init();
    if (!Model_LoadPretrainedWeights()) {
        printf("[WARN] SVM 参数不可用\n");
    }

    Features_InitWindow(&g_can_window);
    Timing_InitPerformanceMarkers(&g_perf_markers);

    /* DWT 自检 */
    Timing_Start(&probe);
    volatile uint32_t x = 0;
    for (uint32_t i = 0; i < 10000u; i++) { x += i; }
    Timing_Stop(&probe);
    printf("DWT 自检: busy-loop(10000) cycles=%lu us=%lu\n",
           (unsigned long)probe.elapsed_cycles, (unsigned long)probe.elapsed_us);
    (void)x;

    printf("\n[1/3] 特征提取性能...\n");  RunFeatureExtractionTest();
    printf("[2/3] 模型推理性能...\n");    RunInferenceTest();
    printf("[3/3] 端到端性能...\n");      RunEndToEndTest();

    PrintStatistics();

    /* 持续心跳 + 每秒重打关键数据，便于串口抓取（不用卡复位时机） */
    uint32_t beat = 0;
    while (1) {
        BOARD_LED_TOGGLE(BOARD_LED0);
        HAL_Delay(MAIN_LOOP_DELAY_MS);
        if ((++beat % 10u) == 0u) {
            printf("beat=%lu clk=%luMHz feat=%.2fus infer=%.2fus e2e=%.2fus atk=%lu/%lu\n",
                   (unsigned long)beat,
                   (unsigned long)Timing_GetClockMHz(),
                   g_perf_markers.feature_stats.mean_us,
                   g_perf_markers.model_stats.mean_us,
                   g_perf_markers.total_stats.mean_us,
                   (unsigned long)g_attack_count, (unsigned long)TEST_ITERATIONS);
        }
    }
}

/* ============================================================================
 * 启动代码：Reset_Handler + 向量表 + 异常处理
 * ============================================================================ */
void Reset_Handler(void)
{
    uint32_t *src;
    uint32_t *dst;

    __asm volatile("ldr sp, =_estack");

    src = &_sidata; dst = &_sdata;
    while (dst < &_edata) { *dst++ = *src++; }
    dst = &_sbss;
    while (dst < &_ebss) { *dst++ = 0u; }

    main();
    while (1) { }
}

void NMI_Handler(void)        { while (1) { } }
void HardFault_Handler(void)  { while (1) { } }
void MemManage_Handler(void)  { while (1) { } }
void BusFault_Handler(void)   { while (1) { } }
void UsageFault_Handler(void) { while (1) { } }
void SVC_Handler(void)        { while (1) { } }
void DebugMon_Handler(void)   { while (1) { } }
void PendSV_Handler(void)     { while (1) { } }

__attribute__((section(".isr_vector"), used))
const uintptr_t g_pfnVectors[] = {
    (uintptr_t)&_estack,
    (uintptr_t)Reset_Handler,
    (uintptr_t)NMI_Handler,
    (uintptr_t)HardFault_Handler,
    (uintptr_t)MemManage_Handler,
    (uintptr_t)BusFault_Handler,
    (uintptr_t)UsageFault_Handler,
    0, 0, 0, 0,
    (uintptr_t)SVC_Handler,
    (uintptr_t)DebugMon_Handler,
    0,
    (uintptr_t)PendSV_Handler,
    (uintptr_t)SysTick_Handler,
};
