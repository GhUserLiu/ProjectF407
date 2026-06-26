/**
 * @file uart_retarget.c
 * @brief USART1 裸寄存器驱动 + newlib _write（printf 重定向）。
 *
 * USART1 在 APB2（84MHz）：BRR = 84MHz / baud。PA9=TX 复用 AF7。
 */
#include "uart_retarget.h"
#include "config.h"

/* ---- 外设基址 ---- */
#define RCC_BASE_ADDR      0x40023800u
#define GPIOA_BASE_ADDR    0x40020000u
#define USART1_BASE_ADDR   0x40011000u

/* RCC 寄存器（仅用到 AHB1ENR / APB2ENR） */
#define RCC_AHB1ENR        (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x30u))
#define RCC_APB2ENR        (*(volatile uint32_t *)(RCC_BASE_ADDR + 0x44u))
#define RCC_AHB1ENR_GPIOA  (1u << 0)
#define RCC_APB2ENR_USART1 (1u << 4)

/* GPIOA 寄存器 */
#define GPIOA_MODER        (*(volatile uint32_t *)(GPIOA_BASE_ADDR + 0x00u))
#define GPIOA_OTYPER       (*(volatile uint32_t *)(GPIOA_BASE_ADDR + 0x04u))
#define GPIOA_OSPEEDR      (*(volatile uint32_t *)(GPIOA_BASE_ADDR + 0x08u))
#define GPIOA_PUPDR        (*(volatile uint32_t *)(GPIOA_BASE_ADDR + 0x0Cu))
#define GPIOA_AFRH         (*(volatile uint32_t *)(GPIOA_BASE_ADDR + 0x24u))  /* pin8..15 */

/* USART1 寄存器 */
#define USART1_SR          (*(volatile uint32_t *)(USART1_BASE_ADDR + 0x00u))
#define USART1_DR          (*(volatile uint32_t *)(USART1_BASE_ADDR + 0x04u))
#define USART1_BRR         (*(volatile uint32_t *)(USART1_BASE_ADDR + 0x08u))
#define USART1_CR1         (*(volatile uint32_t *)(USART1_BASE_ADDR + 0x0Cu))

#define USART_SR_TXE       (1u << 7)
#define USART_SR_TC        (1u << 6)
#define USART_CR1_UE       (1u << 13)
#define USART_CR1_TE       (1u << 3)
#define USART_CR1_RE       (1u << 2)

void USART1_Init_Direct(uint32_t baud)
{
    uint32_t brr;

    /* 1. 使能 GPIOA + USART1 时钟 */
    RCC_AHB1ENR  |= RCC_AHB1ENR_GPIOA;
    RCC_APB2ENR  |= RCC_APB2ENR_USART1;

    /* 2. PA9 = TX：复用功能 AF7(USART1)，推挽，超高速 */
    GPIOA_MODER   &= ~(0x3u << (9u * 2u));   /* 清模式 */
    GPIOA_MODER   |=  (0x2u << (9u * 2u));   /* 10 = 复用功能 */
    GPIOA_OTYPER  &= ~(1u << 9u);            /* 推挽 */
    GPIOA_OSPEEDR |=  (0x3u << (9u * 2u));   /* 超高速 */
    GPIOA_PUPDR   &= ~(0x3u << (9u * 2u));
    GPIOA_PUPDR   |=  (0x1u << (9u * 2u));   /* 上拉 */
    GPIOA_AFRH    &= ~(0xFu << ((9u - 8u) * 4u));
    GPIOA_AFRH    |=  (0x7u << ((9u - 8u) * 4u));  /* AF7 */

    /* PA10 = RX：复用 AF7（即便只做输出，配好便于将来收） */
    GPIOA_MODER   &= ~(0x3u << (10u * 2u));
    GPIOA_MODER   |=  (0x2u << (10u * 2u));
    GPIOA_AFRH    &= ~(0xFu << ((10u - 8u) * 4u));
    GPIOA_AFRH    |=  (0x7u << ((10u - 8u) * 4u));

    /* 3. 波特率（USART1 挂在 APB2 = 84MHz） */
    brr = (APB2_PERIPH_FREQ_HZ + baud / 2u) / baud;
    USART1_BRR = brr;

    /* 4. 使能 USART1，TX（+RX） */
    USART1_CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

void USART1_PutChar(char c)
{
    while ((USART1_SR & USART_SR_TXE) == 0u) { }
    USART1_DR = (uint32_t)(uint8_t)c;
}

void USART1_Write(const char *data, int len)
{
    int i;
    for (i = 0; i < len; i++) {
        if (data[i] == '\n') {
            USART1_PutChar('\r');   /* 换行前补回车，便于串口终端 */
        }
        USART1_PutChar(data[i]);
    }
    while ((USART1_SR & USART_SR_TC) == 0u) { }  /* 等发送完成 */
}

/* newlib 系统调用：把 printf 输出重定向到 USART1 */
int _write(int fd, char *buf, int len)
{
    (void)fd;
    USART1_Write(buf, len);
    return len;
}
