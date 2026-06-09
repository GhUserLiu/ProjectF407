# HAL 库 API 参考

本文档描述了 STM32F407 自定义 HAL 库的 API 接口。

## 模块

| 模块 | 描述 | 头文件 |
|------|------|--------|
| [HAL 核心](#hal-核心) | 基础 HAL 功能 | `stm32f4xx_hal.h` |
| [GPIO](#gpio) | 通用输入输出 | `stm32f4xx_hal.h` |
| [SysTick](#systick) | 系统定时器 | `stm32f4xx_hal.h` |
| [RCC](#rcc) | 时钟控制 | `stm32f4xx_hal_ext.h` |
| [EXTI](#exti) | 外部中断 | `stm32f4xx_hal_ext.h` |
| [NVIC](#nvi-c) | 嵌套中断控制器 | `stm32f4xx_hal_ext.h` |

---

## HAL 核心

### 初始化和去初始化

```c
HAL_StatusTypeDef HAL_Init(void);
```
初始化 HAL 库，配置 SysTick 定时器。

**返回值**: `HAL_OK` 成功，其他值表示错误

```c
HAL_StatusTypeDef HAL_DeInit(void);
```
去初始化 HAL 库，恢复默认状态。

### 时间管理

```c
uint32_t HAL_GetTick(void);
```
获取系统启动后的毫秒数。

**返回值**: 当前系统时间（毫秒）

```c
void HAL_Delay(__IO uint32_t Delay);
```
延时指定的毫秒数。

**参数**:
- `Delay`: 延时时间（毫秒）

```c
void HAL_IncTick(void);
```
SysTick 中断调用，增加系统时间计数。

---

## GPIO

### 时钟使能宏

```c
__HAL_RCC_GPIOA_CLK_ENABLE();
__HAL_RCC_GPIOB_CLK_ENABLE();
__HAL_RCC_GPIOC_CLK_ENABLE();
__HAL_RCC_GPIOD_CLK_ENABLE();
__HAL_RCC_GPIOE_CLK_ENABLE();
__HAL_RCC_GPIOF_CLK_ENABLE();
__HAL_RCC_GPIOG_CLK_ENABLE();
__HAL_RCC_GPIOH_CLK_ENABLE();
```

### 初始化

```c
void HAL_GPIO_Init(GPIO_TypeDef* GPIOx, GPIO_InitTypeDef* GPIO_InitStruct);
```
初始化 GPIO 引脚。

**参数**:
- `GPIOx`: GPIO 端口 (GPIOA-GPIOH)
- `GPIO_InitStruct`: 初始化结构体指针

**初始化结构体**:
```c
typedef struct {
    uint32_t Pin;       // 引脚号 (GPIO_PIN_0 - GPIO_PIN_15)
    uint32_t Mode;      // 模式 (GPIO_MODE_INPUT, GPIO_MODE_OUTPUT_PP, etc.)
    uint32_t Pull;      // 上拉/下拉 (GPIO_NOPULL, GPIO_PULLUP, GPIO_PULLDOWN)
    uint32_t Speed;     // 速度 (GPIO_SPEED_FREQ_LOW/MEDIUM/HIGH/VERY_HIGH)
    uint32_t Alternate; // 复用功能 (0-15)
} GPIO_InitTypeDef;
```

### 读写操作

```c
GPIO_PinState HAL_GPIO_ReadPin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
```
读取 GPIO 引脚状态。

**参数**:
- `GPIOx`: GPIO 端口
- `GPIO_Pin`: 引脚号

**返回值**: `GPIO_PIN_RESET` (0) 或 `GPIO_PIN_SET` (1)

```c
void HAL_GPIO_WritePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin, GPIO_PinState PinState);
```
设置 GPIO 引脚状态。

**参数**:
- `GPIOx`: GPIO 端口
- `GPIO_Pin`: 引脚号
- `PinState`: `GPIO_PIN_RESET` 或 `GPIO_PIN_SET`

```c
void HAL_GPIO_TogglePin(GPIO_TypeDef* GPIOx, uint16_t GPIO_Pin);
```
切换 GPIO 引脚状态。

---

## SysTick

系统定时器由 HAL 库自动配置，提供 1ms 时基。

### SysTick_Handler

```c
void SysTick_Handler(void);
```
SysTick 中断处理函数，在 `stm32f4xx_hal.c` 中实现。

---

## RCC

复位和时钟控制模块在 `stm32f4xx_hal_ext.h` 中提供扩展功能。

---

## EXTI

外部中断/事件控制器在 `stm32f4xx_hal_ext.h` 中提供。

---

## NVIC

嵌套向量中断控制器在 `stm32f4xx_hal_ext.h` 中提供。

### 中断优先级

```c
void NVIC_SetPriority(IRQn_Type IRQn, uint32_t priority);
```
设置中断优先级。

---

## 数据类型

| 类型 | 描述 |
|------|------|
| `HAL_StatusTypeDef` | HAL 状态枚举 (HAL_OK, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT) |
| `GPIO_PinState` | GPIO 引脚状态 (GPIO_PIN_RESET=0, GPIO_PIN_SET=1) |
| `FlagStatus`, `ITStatus` | 标志状态 (RESET=0, SET=1) |

---

## 使用示例

### LED 控制

```c
#include "stm32f4xx_hal.h"
#include "board.h"

void GPIO_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOF_CLK_ENABLE();

    GPIO_InitStruct.Pin = BOARD_LED0_PIN;
    GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_HIGH;
    HAL_GPIO_Init(BOARD_LED0_PORT, &GPIO_InitStruct);
}

int main(void)
{
    HAL_Init();
    GPIO_Init();

    while (1) {
        HAL_GPIO_TogglePin(BOARD_LED0_PORT, BOARD_LED0_PIN);
        HAL_Delay(500);
    }
}
```

### 按键读取

```c
uint8_t Read_KEY(void)
{
    return HAL_GPIO_ReadPin(KEY_PORT, KEY_PIN) == GPIO_PIN_SET;
}
```
