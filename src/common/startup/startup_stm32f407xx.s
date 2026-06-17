/*
 * startup_stm32f407xx.s — 公共启动文件占位（说明）
 * ====================================================================
 *
 * 本文件当前为【占位说明】，不包含有效的启动代码。
 *
 * 项目现状（保守策略：不改动 C 代码与构建链接逻辑）：
 *
 *  1. 简单项目（如 src/projects/01-turn-signal/）
 *     启动逻辑（Reset_Handler 及必要的中断向量）由各项目自身的 main.c
 *     以直接寄存器操作的方式内嵌实现，不依赖本公共启动文件的内容。
 *
 *  2. CubeMX 项目（如 src/projects/07-car-gear/）
 *     使用各自 cubemx/ 目录下 CubeMX 生成的完整启动文件：
 *         src/projects/07-car-gear/cubemx/startup_stm32f407xx.s
 *     （含完整中断向量表与 Reset_Handler，约 23KB）。
 *
 *  3. 本文件 src/common/startup/startup_stm32f407xx.s
 *     Makefile（ASM_SOURCES）会引用它，但历史上其内容为误重定向产生的
 *     无效文本（"​-E / common/startup/..."），并非有效汇编。
 *     此处已清理为纯说明注释，避免误导。
 *
 * 如需让“简单项目统一使用公共启动文件”，可从 CubeMX 项目拷贝完整启动
 * 文件覆盖本文件，并移除各项目 main.c 中内嵌的 Reset_Handler：
 *     cp src/projects/07-car-gear/cubemx/startup_stm32f407xx.s \
 *        src/common/startup/startup_stm32f407xx.s
 * 该改造涉及 C 代码与链接行为，需在有 arm-none-eabi-gcc 工具链的环境下
 * 实测编译/烧录验证后再合入。
 *
 * 注意：保留为纯注释时，本文件可被汇编器处理为空目标文件，不引入任何指令。
 */
