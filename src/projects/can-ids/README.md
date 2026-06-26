# CAN 入侵检测系统 — STM32F407 部署（INT8 线性 SVM）

在 STM32F407 上部署一个 **INT8 量化的线性 SVM**，对 CAN 总线流量窗口做入侵/正常
二分类，并用 **DWT 周期计数器**实测特征提取与推理的墙钟时间（µs）。

本项目是 `stm32_deployment.zip` 原版的修复 + 仓库集成版：原版计时为写死的假数据、
模型权重全零恒判攻击、HAL/printf 全注释、且号称的"INT8"实际是 float MLP。本版改为
真正的 INT8 线性 SVM（全整型核心推理），并接入仓库构建系统。

## 模型：INT8 线性 SVM

- 决策：`f(x) = w·x + b`，攻击 ⟺ `f(x) >= 0`。二分类（0=正常，1=攻击），17 维特征。
- **核心分类全整型**：
  - 输入量化：`x_q[i] = clamp(round(x[i]/s_x[i]), -128, 127)`（每维独立 scale）
  - 折叠：`w_eff[i] = w[i]·s_x[i]` → 单一权重 scale `s_w` → `w_q[i] = round(w_eff[i]/s_w)` int8
  - 点积：`dot = Σ w_q[i]·x_q[i]`（int32）
  - 判定：`攻击 ⟺ dot >= threshold`，`threshold = round(-b/s_w)` 已折叠所有 scale
- 边缘浮点（校准元数据，不影响整型决策）：输入量化（17 次 ÷）与 Platt 概率（1 次 `expf`）。
- **int8 模型体积**：`w_q` = 17 字节 int8 + `threshold`(int32,4B) + 校准元数据
  `s_x[17]`/`s_w`/`b`/`platt_A`/`platt_B`（≈105B，const 链入 FLASH，0 字节 RAM）。
- 训练侧 int8 精度：合成数据上 float acc = int8 acc = 1.0000（量化零损失）。

## 构建与烧录

```bash
make PROJECT=can-ids            # debug (-O0)
make PROJECT=can-ids release    # -O2（更贴近真实时延）
make PROJECT=can-ids size
make PROJECT=can-ids flash      # ST-Link
```

产物：`outputs/build/can-ids/{debug,release}/can-ids.{elf,bin,hex}`。
串口：USART1 PA9(TX)/PA10(RX)，**115200 8N1**（板载 CH340C，需跳线帽）。

## 训练与校验（sklearn，本机可跑）

```bash
python src/projects/can-ids/train_svm.py    # 训练 + 量化 + 导出 model_weights.c/.h + golden
python src/projects/can-ids/golden_test.py  # INT8 导出契约自洽校验
```

`train_svm.py` 用 `sklearn.svm.LinearSVC` 训练 float SVM → 每维输入 scale → 折叠到 int8
`w_q` + 整数 `threshold` → Platt 概率校准（`LogisticRegression`）→ 验证 int8 精度 → 导出。

## 文件说明

| 文件 | 作用 |
|------|------|
| `main_interrupt.c` | 主程序：内嵌启动、168MHz 时钟、DWT 自检、3 项基准、报告、CAN 回调 |
| `timing.c/.h` | DWT µs 计时（替换原 mock TIM2） |
| `features.c/.h` | 17 维 CAN 特征提取（大缓冲转 static、间隔单调保护、熵=nats） |
| `model.c/.h` | **INT8 线性 SVM 推理**（int32 点积 vs 整数阈值） |
| `model_weights.c/.h` | **训练器生成**的 SVM 参数（const int8 + 元数据） |
| `uart_retarget.c/.h` | 裸寄存器 USART1 + printf 重定向 |
| `syscalls.c` | newlib-nano 桩（`_sbrk`、`__errno`） |
| `train_svm.py` | sklearn 训练 + int8 量化 + 导出 + golden |
| `golden_test.py` | host 侧导出契约自洽校验 |

## 上机预期输出（115200）

```
==========================================
CAN 入侵检测系统 - STM32F407
==========================================
SystemCoreClock = 168000000 Hz (clock_mhz=168)
模型: INT8 线性 SVM (17 维特征, w_q=17B int8 + 整数阈值)
DWT 自检: busy-loop(10000) cycles=59524 us=354
[1/3] 特征提取性能...   单次特征提取: <real> us ...
[2/3] 模型推理性能...   单次推理: <real> us (正常=.. 攻击=.. score=.. -> ..)
[3/3] 端到端性能...
========== 最终测量报告（100 次迭代） ==========
【特征提取】 avg=<real> us  min=..  max=..
【模型推理】 avg=<real> us  min=..  max=..
【端到端  】 avg=<real> us  min=..  max=..
【处理能力】 窗口处理速率: <real> 窗口/秒  消息处理速率: <real> 消息/秒
【分类统计】 正常=..  攻击=..  端到端处理=100
```

判定真实计时生效：avg/min/max 各不同（原版恒为 100）；推理 score 非零、决策非恒定。

## 相对原版的修复

| 原版问题 | 修复 |
|---|---|
| 计时恒为 100µs（mock） | DWT 周期计数器真实测量 |
| float MLP 冒充"INT8"、权重全零恒判攻击 | 真正 INT8 线性 SVM，全整型核心推理，const 参数 |
| TF 训练管线断裂（本机无 TF） | sklearn 训练 + 手工 int8 量化，本地可跑 |
| HAL/时钟/printf 全注释 | 内嵌向量表+Reset、真实 168MHz、USART1 printf 重定向 |
| features.c ~5.9KB 栈帧 | 大缓冲转文件级 static |
| 时间间隔 uint32 下溢 | 单调保护 |
| 吞吐量标签 100× 误标 | 窗口率/消息率分别标注 |

并修复仓库 Makefile 两处既有缺陷（`CFLAGS` 递归自引用；`make release` 丢 `BUILD_TYPE`），
链接栈 0x400→0x1000。

## 风险与未在本地验证项

- **HSE 晶振**：假定为 8MHz。`SystemClock_Config` 带 HSE 超时回退 HSI（16MHz），均 PLL→168MHz。
- **numpy/sklearn↔C 一致性**：本机无 host gcc/QEMU；由「公式契约 + 导出自洽校验 + 上机 UART 抽查」保证。
- **运行期 CAN**：`CAN_RxMessage_Handler` 是集成点（已接特征→SVM→告警），但未初始化 bxCAN 外设（计时实验不需要）。

## 许可

教学/研究用途。
