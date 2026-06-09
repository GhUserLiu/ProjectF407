# 板级支持包 (BSP) API 参考

本文档描述了 M144Z-M4 开发板的硬件抽象层 API。

## 概述

`board.h` 定义了 M144Z-M4 开发板 (STM32F407ZGTx) 的固定硬件配置，包括：
- LED 引脚定义
- 按键引脚定义
- 可用 GPIO 列表
- 调试接口定义
- 串口引脚定义

**注意**: `board.h` 中的定义是开发板固定的，通常不需要修改。

---

## 宏定义

### 开发板信息

```c
#define BOARD_NAME     "M144Z-M4"
#define BOARD_MCU      "STM32F407ZGTx"
#define BOARD_SYSCLK_FREQ  168000000UL  // 168MHz
```

---

## LED

### 引脚定义

```c
// LED0 - 左转向灯
#define BOARD_LED0_PORT  GPIOF
#define BOARD_LED0_PIN   GPIO_PIN_9

// LED1 - 右转向灯
#define BOARD_LED1_PORT  GPIOF
#define BOARD_LED1_PIN   GPIO_PIN_10
```

### 控制宏

LED 类型：共阳极，**低电平点亮**

```c
// 点亮 LED（低电平）
BOARD_LED_ON(BOARD_LED0);

// 熄灭 LED（高电平）
BOARD_LED_OFF(BOARD_LED1);

// 切换 LED 状态
BOARD_LED_TOGGLE(BOARD_LED0);
```

### 使用示例

```c
#include "board.h"

void LED_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOF_CLK_ENABLE();

    GPIO_InitStruct.Pin = BOARD_LED0_PIN | BOARD_LED1_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(BOARD_LED0_PORT, &GPIO_InitStruct);

    // 初始状态：熄灭
    BOARD_LED_OFF(BOARD_LED0);
    BOARD_LED_OFF(BOARD_LED1);
}

void LED_Blink(void)
{
    BOARD_LED_TOGGLE(BOARD_LED0);
    HAL_Delay(500);
}
```

---

## 按键

### 引脚定义

```c
// KEY0 - PE4，模式切换 / BOOT0
#define BOARD_KEY0_PORT  GPIOE
#define BOARD_KEY0_PIN   GPIO_PIN_4

// KEY_UP - PA0，双闪开关 / WKUP
#define BOARD_KEY_UP_PORT  GPIOA
#define BOARD_KEY_UP_PIN   GPIO_PIN_0
```

### 触发方式

触发方式（高/低电平）由项目配置文件 `config.h` 决定：

```c
// 在 config.h 中定义
#define KEY0_TRIGGER_HIGH   1   // 1=高电平触发, 0=低电平触发
#define KEY_UP_TRIGGER_HIGH  0
```

### 使用示例

```c
#include "board.h"
#include "config.h"

void KEY_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();

    GPIO_InitStruct.Pin = BOARD_KEY0_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = KEY_PULL(KEY0_TRIGGER_HIGH);
    HAL_GPIO_Init(BOARD_KEY0_PORT, &GPIO_InitStruct);

    GPIO_InitStruct.Pin = BOARD_KEY_UP_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = KEY_PULL(KEY_UP_TRIGGER_HIGH);
    HAL_GPIO_Init(BOARD_KEY_UP_PORT, &GPIO_InitStruct);
}

uint8_t KEY0_IsPressed(void)
{
    GPIO_PinState state = HAL_GPIO_ReadPin(BOARD_KEY0_PORT, BOARD_KEY0_PIN);
    return KEY0_TRIGGER_HIGH ? (state == GPIO_PIN_SET) : (state == GPIO_PIN_RESET);
}
```

---

## 可用 GPIO

以下引脚可用作通用 GPIO 输入/输出：

```c
// Port A
BOARD_GPIO_PA1   // PA1
BOARD_GPIO_PA2   // PA2
BOARD_GPIO_PA3   // PA3
BOARD_GPIO_PA5   // PA5
BOARD_GPIO_PA7   // PA7
BOARD_GPIO_PA15  // PA15

// Port B
BOARD_GPIO_PB10  // PB10
BOARD_GPIO_PB11  // PB11
BOARD_GPIO_PB12  // PB12
BOARD_GPIO_PB13  // PB13

// Port C
BOARD_GPIO_PC0   // PC0
BOARD_GPIO_PC1   // PC1
BOARD_GPIO_PC2   // PC2
BOARD_GPIO_PC3   // PC3
BOARD_GPIO_PC4   // PC4
BOARD_GPIO_PC5   // PC5

// Port D
BOARD_GPIO_PD3   // PD3

// Port E
BOARD_GPIO_PE2   // PE2
BOARD_GPIO_PE3   // PE3

// Port F
BOARD_GPIO_PF6   // PF6
BOARD_GPIO_PF7   // PF7
BOARD_GPIO_PF8   // PF8

// Port G
BOARD_GPIO_PG6   // PG6
BOARD_GPIO_PG7   // PG7
BOARD_GPIO_PG8   // PG8
BOARD_GPIO_PG11  // PG11
BOARD_GPIO_PG13  // PG13
BOARD_GPIO_PG14  // PG14
BOARD_GPIO_PG15  // PG15
```

### 使用示例

```c
#define BOARD_SENSOR_PORT  GPIOB
#define BOARD_SENSOR_PIN   BOARD_GPIO_PB10

void SENSOR_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOB_CLK_ENABLE();

    GPIO_InitStruct.Pin = BOARD_SENSOR_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(BOARD_SENSOR_PORT, &GPIO_InitStruct);
}
```

---

## 调试接口

```c
#define BOARD_SWDIO_PIN  GPIO_PIN_13  // PA13
#define BOARD_SWCLK_PIN  GPIO_PIN_14  // PA14
```

这些引脚用于 SWD 调试，通常不应作他用。

---

## 串口

CH340C USB 转串口引脚（需跳线帽连接）：

```c
#define BOARD_USART1_TX_PORT  GPIOA
#define BOARD_USART1_TX_PIN   GPIO_PIN_9

#define BOARD_USART1_RX_PORT  GPIOA
#define BOARD_USART1_RX_PIN   GPIO_PIN_10
```

---

## 完整示例

```c
#include <stdint.h>
#include "stm32f4xx_hal.h"
#include "board.h"
#include "config.h"

void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    // LED
    __HAL_RCC_GPIOF_CLK_ENABLE();
    GPIO_InitStruct.Pin = BOARD_LED0_PIN | BOARD_LED1_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(BOARD_LED0_PORT, &GPIO_InitStruct);

    // 按键
    __HAL_RCC_GPIOE_CLK_ENABLE();
    GPIO_InitStruct.Pin = BOARD_KEY0_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = KEY_PULL(KEY0_TRIGGER_HIGH);
    HAL_GPIO_Init(BOARD_KEY0_PORT, &GPIO_InitStruct);
}

int main(void)
{
    HAL_Init();
    GPIO_Init();

    while (1) {
        BOARD_LED_TOGGLE(BOARD_LED0);
        HAL_Delay(MAIN_LOOP_DELAY);
    }

    return 0;
}
```
