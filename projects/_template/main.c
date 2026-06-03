/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : STM32F407 项目模板
  ******************************************************************************
  */

#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "board.h"
#include "config.h"

/* ========== 全局变量 ========== */




/* ========== 函数声明 ========== */
void SystemClock_Config(void);
void GPIO_Init(void);

/* ========== HAL初始化 ========== */
void SystemClock_Config(void)
{
  /* 使用默认HSI时钟，暂不配置PLL */
}

/* ========== GPIO初始化 ========== */
void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* 使能GPIO时钟 */
    __HAL_RCC_GPIOA_CLK_ENABLE();

    /* TODO: 配置你的引脚 */
    /* 示例：配置LED */
    // GPIO_InitStruct.Pin = BOARD_LED0_PIN;
    // GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    // GPIO_InitStruct.Pull = GPIO_NOPULL;
    // GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    // HAL_GPIO_Init(BOARD_LED0_PORT, &GPIO_InitStruct);
}

/* ========== 主函数 ========== */
int main(void)
{
    /* HAL初始化 */
    HAL_Init();
    SystemClock_Config();

    /* GPIO初始化 */
    GPIO_Init();

    /* 主循环 */
    while (1)
    {
        /* TODO: 你的代码 */
        HAL_Delay(MAIN_LOOP_DELAY);
    }

    return 0;
}

/* ========== 异常处理 ========== */
void NMI_Handler(void)        { while (1); }
void HardFault_Handler(void)  { while (1); }
void MemManage_Handler(void)  { while (1); }
void BusFault_Handler(void)   { while (1); }
void UsageFault_Handler(void) { while (1); }
void SVC_Handler(void)        { while (1); }
void DebugMon_Handler(void)   { while (1); }
void PendSV_Handler(void)     { while (1); }
