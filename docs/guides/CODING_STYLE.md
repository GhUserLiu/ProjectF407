# 代码风格指南

本文档定义了 STM32F407 项目的编码风格规范。

## 命名规范

### 文件命名

- **C 源文件**: 小写，下划线分隔 → `stm32f4xx_hal.c`
- **头文件**: 小写，下划线分隔 → `stm32f4xx_hal.h`

### 变量命名

```c
// 全局变量：小写，下划线分隔
uint32_t toggle_counter = 0;
volatile uint8_t led0_state = 1;

// 局部变量：小写，下划线分隔
uint8_t key0_now, key_up_now;

// 常量：大写，下划线分隔
#define MAX_COUNT  100
#define LED_PIN    GPIO_PIN_9
```

### 函数命名

```c
// 函数名：大驼峰（PascalCase），单词首字母大写
void SystemClock_Config(void);
void GPIO_Init(void);
uint8_t Read_KEY0(void);
void LED_Update(void);

// HAL 函数：模块名_功能_操作
HAL_GPIO_Init(...);
HAL_GPIO_WritePin(...);
```

### 类型定义

```c
// 枚举类型：大驼峰 + _t 后缀
typedef enum {
    MODE_OFF = 0,
    MODE_LEFT,
    MODE_RIGHT
} LightMode;  // 或 LightMode_t

// 结构体：大驼峰 + _t 后缀
typedef struct {
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Speed;
} GPIO_InitTypeDef;
```

## 格式规范

### 缩进和对齐

- 使用 4 个空格缩进
- 不使用 Tab 字符
- 大括号独占一行（Allman 风格）

```c
void Function_Name(void)
{
    if (condition)
    {
        Do_Something();
    }
    else
    {
        Do_Other_Thing();
    }
}
```

### 注释规范

```c
/* ========== 单行注释 ========== */

/* ========== 分隔注释（用于分隔代码区域） ========== */

/**
  ******************************************************************************
  * @file    : filename.h
  * @brief   : 简短描述
  ******************************************************************************
  */

/**
  * @brief  函数简短描述
  * @param  param1: 参数1描述
  * @retval 返回值描述
  */
```

## 代码组织

### 头文件结构

```c
#ifndef __FILENAME_H
#define __FILENAME_H

#ifdef __cplusplus
extern "C" {
#endif

/* ========== 包含头文件 ========== */
#include <stdint.h>
#include "stm32f4xx_hal.h"

/* ========== 宏定义 ========== */
#define CONFIG_VALUE  100

/* ========== 类型定义 ========== */
typedef enum { ... } MyEnum;

/* ========== 函数声明 ========== */
void Function_Name(void);

#ifdef __cplusplus
}
#endif

#endif /* __FILENAME_H */
```

### 源文件结构

```c
/* ========== 包含头文件 ========== */
#include "main.h"

/* ========== 全局变量 ========== */
volatile uint8_t flag = 0;

/* ========== 私有变量 ========== */
static uint32_t counter = 0;

/* ========== 函数声明 ========== */
static void Private_Function(void);

/* ========== 函数定义 ========== */
void Public_Function(void)
{
    // ...
}

static void Private_Function(void)
{
    // ...
}
```

## 最佳实践

### 1. 使用 volatile 关键字

对可能在中断中修改的变量使用 `volatile`：

```c
volatile uint32_t system_tick = 0;
```

### 2. 检查返回值

检查 HAL 函数的返回值：

```c
if (HAL_GPIO_Init(...) != HAL_OK)
{
    Error_Handler();
}
```

### 3. 避免魔术数字

使用宏定义替代魔术数字：

```c
// 好的做法
#define LED_TOGGLE_INTERVAL  25
if (toggle_counter >= LED_TOGGLE_INTERVAL)

// 不好的做法
if (toggle_counter >= 25)
```

### 4. 使用位操作宏

对于位操作，使用定义好的宏：

```c
// 设置位
REG |= (1U << BIT_POS);

// 清除位
REG &= ~(1U << BIT_POS);

// 切换位
REG ^= (1U << BIT_POS);
```

## 工具支持

项目包含 `.clang-format` 配置文件，可以自动格式化代码。

### VSCode 格式化

保存时自动格式化（在 `.vscode/settings.json` 中配置）：

```json
{
    "editor.formatOnSave": true
}
```

### 手动格式化

```bash
# 格式化单个文件
clang-format -i filename.c

# 格式化整个项目
find . -name "*.c" -o -name "*.h" | xargs clang-format -i
```
