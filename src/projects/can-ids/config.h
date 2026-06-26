/**
 ******************************************************************************
 * @file    : config.h
 * @brief   : CAN 入侵检测系统 - 项目配置（STM32F407，计时优先验证）
 ******************************************************************************
 */
#ifndef __CONFIG_H
#define __CONFIG_H

/* ========== 时钟配置 ========== */
#define SYSCLK_FREQ_168M        168000000UL     /* PLL 目标主频 */
#define HSE_FREQ_HZ             8000000UL       /* M144Z-M4 外部晶振（推断，见 README 风险） */
#define HSI_FREQ_HZ             16000000UL      /* 内部 HSI */
#define APB2_PERIPH_FREQ_HZ     84000000UL      /* USART1 所在总线频率（=SYSCLK/2） */

/* ========== UART 输出配置 ========== */
#define UART_BAUDRATE           115200          /* printf 输出波特率（CH340C USB 串口） */

/* ========== 运行期可调参数 ========== */
/* 模型维度(MODEL_*)在 model.h；窗口(CAN_WINDOW_SIZE/FEATURE_DIM)在 features.h */
#define TEST_ITERATIONS         100             /* 性能测试迭代次数 */
#define ATTACK_THRESHOLD        0.5f            /* 攻击判定阈值 */

/* ========== 主循环 ========== */
#define MAIN_LOOP_DELAY_MS      100

#endif /* __CONFIG_H */
