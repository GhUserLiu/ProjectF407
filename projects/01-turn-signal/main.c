/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : STM32F407 转向灯 - HAL库版本
  *                 LED: 共阳极，低电平点亮
  ******************************************************************************
  */

#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "board.h"
#include "config.h"

/* ========== 模式定义 ========== */
typedef enum {
    MODE_OFF = 0,
    MODE_LEFT,
    MODE_RIGHT,
    MODE_HAZARD
} LightMode;

volatile LightMode light_mode = MODE_OFF;
volatile LightMode previous_mode = MODE_OFF;
volatile uint8_t led0_state = 1;  /* 1=灭, 0=亮（低电平点亮） */
volatile uint8_t led1_state = 1;
volatile uint32_t toggle_counter = 0;

/* ========== 按键状态变量 ========== */
static uint8_t key0_pressed = 0;
static uint8_t key_up_pressed = 0;

/* ========== HAL初始化 ========== */
void SystemClock_Config(void)
{
  /* 使用默认HSI时钟，暂不配置PLL */
}

/* ========== GPIO初始化（HAL库） ========== */
void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    /* 配置KEY_UP引脚 */
    GPIO_InitStruct.Pin = BOARD_KEY_UP_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = KEY_PULL(KEY_UP_TRIGGER_HIGH);
    HAL_GPIO_Init(BOARD_KEY_UP_PORT, &GPIO_InitStruct);

    /* 配置KEY0引脚 */
    GPIO_InitStruct.Pin = BOARD_KEY0_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = KEY_PULL(KEY0_TRIGGER_HIGH);
    HAL_GPIO_Init(BOARD_KEY0_PORT, &GPIO_InitStruct);
}

/* ========== 读取按键状态 ========== */
uint8_t Read_KEY0(void)
{
    GPIO_PinState pin_state = HAL_GPIO_ReadPin(BOARD_KEY0_PORT, BOARD_KEY0_PIN);
    return KEY0_TRIGGER_HIGH ? pin_state : !pin_state;
}

uint8_t Read_KEY_UP(void)
{
    GPIO_PinState pin_state = HAL_GPIO_ReadPin(BOARD_KEY_UP_PORT, BOARD_KEY_UP_PIN);
    return KEY_UP_TRIGGER_HIGH ? pin_state : !pin_state;
}

/* ========== 按键扫描 ========== */
void Key_Scan(void)
{
    uint8_t key0_now, key_up_now;

    key0_now = Read_KEY0();
    key_up_now = Read_KEY_UP();

    /* 检测KEY0按下（上升沿触发） */
    if (key0_now && !key0_pressed)
    {
        HAL_Delay(KEY_DEBOUNCE_DELAY);
        if (Read_KEY0())
        {
            light_mode = (LightMode)((light_mode + 1) % 4);
            if (light_mode != MODE_HAZARD)
                previous_mode = light_mode;
            toggle_counter = 0;
        }
    }
    key0_pressed = key0_now;

    /* 检测KEY_UP按下（上升沿触发）- 记忆模式↔HAZARD切换 */
    if (key_up_now && !key_up_pressed)
    {
        HAL_Delay(KEY_DEBOUNCE_DELAY);
        if (Read_KEY_UP())
        {
            if (light_mode == MODE_HAZARD)
                light_mode = previous_mode;
            else
            {
                previous_mode = light_mode;
                light_mode = MODE_HAZARD;
            }
            toggle_counter = 0;
        }
    }
    key_up_pressed = key_up_now;
}

/* ========== 更新LED显示 ========== */
void LED_Update(void)
{
    /* 双闪模式频率是普通模式的2倍 */
    uint16_t interval = (light_mode == MODE_HAZARD) ?
                        (LED_TOGGLE_COUNT / 2) : LED_TOGGLE_COUNT;
    toggle_counter++;

    if (toggle_counter >= interval)
    {
        toggle_counter = 0;

        switch(light_mode)
        {
            case MODE_LEFT:
                led0_state = !led0_state;
                led1_state = 1;
                break;

            case MODE_RIGHT:
                led1_state = !led1_state;
                led0_state = 1;
                break;

            case MODE_HAZARD:
                led0_state = !led0_state;
                led1_state = led0_state;
                break;

            default:
                led0_state = 1;
                led1_state = 1;
                break;
        }
    }

    /* 输出LED（低电平点亮：led_state=0时亮，led_state=1时灭） */
    HAL_GPIO_WritePin(BOARD_LED0_PORT, BOARD_LED0_PIN, led0_state ? GPIO_PIN_SET : GPIO_PIN_RESET);
    HAL_GPIO_WritePin(BOARD_LED1_PORT, BOARD_LED1_PIN, led1_state ? GPIO_PIN_SET : GPIO_PIN_RESET);
}

/* ========== 外部变量 ========== */
extern uint32_t _estack;
extern uint32_t _sidata, _sdata, _edata;
extern uint32_t _sbss, _ebss;

/* ========== 主函数 ========== */
int main(void)
{
    /* HAL初始化 */
    HAL_Init();
    SystemClock_Config();

    /* GPIO初始化（按键部分由HAL初始化，LED已在Reset_Handler中初始化） */
    GPIO_Init();

    /* 主循环 */
    while (1)
    {
        Key_Scan();
        LED_Update();
        HAL_Delay(MAIN_LOOP_DELAY);
    }

    return 0;
}

/* ========== 寄存器地址定义 ========== */
#define RCC_AHB1ENR_ADDR   (*(volatile uint32_t*)0x40023830)
#define GPIOF_BASE         0x40021400
#define GPIOF_MODER_ADDR   (*(volatile uint32_t*)(GPIOF_BASE + 0x00))
#define GPIOF_ODR_ADDR     (*(volatile uint32_t*)(GPIOF_BASE + 0x14))

/* ========== Reset_Handler - 直接操作寄存器初始化LED ========== */
void Reset_Handler(void)
{
    uint32_t *src, *dst;

    /* 设置栈指针 */
    __asm volatile("ldr sp, =_estack");

    /* 复制data段 */
    src = &_sidata;
    dst = &_sdata;
    while (dst < &_edata)
        *dst++ = *src++;

    /* 清零bss段 */
    dst = &_sbss;
    while (dst < &_ebss)
        *dst++ = 0;

    /* ========== GPIOF LED寄存器初始化（成功测试版本） ========== */
    /* 1. 使能GPIOF时钟 (AHB1ENR bit 5) */
    RCC_AHB1ENR_ADDR |= (1U << 5);

    /* 2. 配置PF9和PF10为输出模式 */
    GPIOF_MODER_ADDR &= ~(0x3U << (9 * 2));   // 清除PF9模式位
    GPIOF_MODER_ADDR |= (0x1U << (9 * 2));     // 设置PF9为通用输出
    GPIOF_MODER_ADDR &= ~(0x3U << (10 * 2));  // 清除PF10模式位
    GPIOF_MODER_ADDR |= (0x1U << (10 * 2));    // 设置PF10为通用输出

    /* 3. 初始LED状态：灭（高电平） */
    GPIOF_ODR_ADDR |= (1U << 9);   // PF9 = 1
    GPIOF_ODR_ADDR |= (1U << 10);  // PF10 = 1

    /* 调用主函数 */
    main();

    while (1)
    {
        /* 不应该到达这里 */
    }
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
