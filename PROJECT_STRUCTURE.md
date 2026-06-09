# 项目结构说明

## 模块化组织

本项目采用模块化的目录结构，便于代码组织和维护。

```
NewProjectF407/
├── projects/              # 各个实验项目
│   ├── _template/         # 项目模板
│   ├── 01-turn-signal/    # 转向灯系统
│   ├── 07-car-gear/      # 汽车档位 (CubeMX)
│   └── Test6/            # 示例项目
│
├── common/                # 共享代码库（模块化）
│   ├── core/             # 核心 HAL 库
│   │   ├── stm32f4xx_hal.h/c       # 基础 HAL
│   │   └── stm32f4xx_hal_ext.h/c   # 扩展 HAL
│   ├── bsp/              # 板级支持包
│   │   └── board.h                   # 开发板硬件定义
│   ├── drivers/          # 外设驱动（预留）
│   ├── utils/            # 工具函数（预留）
│   ├── inc/              # 公共头文件
│   └── startup/          # 启动文件
│       └── startup_stm32f407xx.s
│
├── docs/                 # 文档中心
│   ├── guides/           # 开发指南
│   ├── api/              # API 文档
│   ├── hardware/         # 硬件文档
│   ├── teaching/         # 教学资料
│   ├── EIDE_GUIDE.md
│   └── TROUBLESHOOTING_LOG.md
│
├── tools/                # 开发工具
│   ├── scripts/          # 辅助脚本
│   └── templates/        # 文件模板
│
├── build/                # 构建输出
├── .vscode/              # VSCode 配置
├── .eide/                # EIDE 配置
├── Makefile              # 构建脚本
├── STM32F407XX_FLASH.ld  # 链接脚本
└── README.md            # 项目说明
```

## 模块说明

### common/core/
核心 HAL 库实现，包含：
- GPIO 操作
- SysTick 定时器
- 基础时钟控制
- 扩展功能（RCC, EXTI, NVIC）

### common/bsp/
板级支持包，定义：
- LED 引脚和控制宏
- 按键引脚
- 可用 GPIO 列表
- 调试接口
- 串口引脚

### common/drivers/
预留的外设驱动目录，可添加：
- UART 驱动
- SPI 驱动
- I2C 驱动
- Timer 驱动
- ADC 驱动

### common/utils/
预留的工具函数目录，可添加：
- 数学函数库
- 字符串处理
- 数据结构
- 协议实现

## 依赖关系

```
项目代码 (projects/XX/)
    ↓
board.h (common/bsp/)
    ↓
stm32f4xx_hal.h (common/core/)
    ↓
stm32f4xx.h (common/inc/)
    ↓
寄存器定义
```

## 扩展指南

### 添加新的驱动模块

1. 在 `common/drivers/` 创建对应目录
2. 实现驱动接口
3. 在项目中包含对应头文件
4. 更新 Makefile（如需要）

### 支持新的芯片系列

1. 在 `common/core/` 下创建芯片特定目录
2. 添加对应的头文件和源文件
3. 通过编译宏切换

### 添加工具函数

1. 在 `common/utils/` 创建对应文件
2. 实现工具函数
3. 在项目中包含使用
