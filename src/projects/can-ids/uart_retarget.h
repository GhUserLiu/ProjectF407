/**
 * @file uart_retarget.h
 * @brief 裸寄存器 USART1 驱动 + printf 重定向声明。
 *
 * 仓库 src/common/drivers/uart/uart.c 依赖简化版 HAL 未提供的
 * USART_TypeDef/HAL_UART_Init 等，编译不过；此处自写最小寄存器版。
 */
#ifndef UART_RETARGET_H
#define UART_RETARGET_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* 初始化 USART1（PA9=TX, PA10=RX），TX 用于 printf 输出。baud 例如 115200。 */
void USART1_Init_Direct(uint32_t baud);

/* 阻塞发送一字节 / 一段。供 _write 调用。 */
void USART1_PutChar(char c);
void USART1_Write(const char *data, int len);

#ifdef __cplusplus
}
#endif
#endif /* UART_RETARGET_H */
