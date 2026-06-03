# STM32F407 项目集合

> 开发板: M144Z-M4最小系统板 (STM32F407ZGTx)

---

## 项目结构

```
NewProjectF407/
├── projects/           # 各个小项目
│   ├── _template/      # 新项目模板
│   ├── 01-turn-signal/ # 转向灯系统
│   └── Test6/          # 资料文档
├── common/             # 共享代码库
│   ├── hal/            # HAL库
│   │   ├── board.h     # 开发板固定硬件配置 ⭐
│   │   └── stm32f4xx_hal.h/c
│   ├── inc/            # 共享头文件
│   └── startup_stm32f407xx.s
├── docs/               # 项目文档
├── build/              # 构建输出
├── Makefile            # 构建脚本
└── STM32F407XX_FLASH.ld
```

---

## 配置说明

### 硬件固定配置 (`common/hal/board.h`)
开发板固定的引脚分配，**无需修改**：
- LED0/LED1 位置
- 按键位置
- 可用GPIO列表

### 项目特定配置 (`projects/XX/config.h`)
根据项目需求配置：
- 按键触发方式（高/低电平）
- 时序参数
- 项目特定功能开关

---

## 构建命令

```bash
# 构建默认项目
make

# 构建指定项目
make PROJECT=01-turn-signal

# 列出所有项目
make list

# 清理
make clean
```

---

## 新建项目

```bash
# 1. 复制模板
cp -r projects/_template projects/02-your-project

# 2. 修改 projects/02-your-project/config.h

# 3. 编写 projects/02-your-project/main.c

# 4. 构建
make PROJECT=02-your-project
```

---

## 项目列表

| 编号 | 项目 | 状态 |
|------|------|------|
| 01 | 转向灯系统 | 进行中 |
| - | Test6 | 资料文档 |
