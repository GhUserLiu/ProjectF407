/**
 * @file syscalls.c
 * @brief newlib-nano 最小系统调用桩。
 *
 * -nostartfiles + -specs=nano.specs 下：
 *  - printf/vsnprintf 需要 _sbrk（堆）；
 *  - libm 的 expf/sqrtf 在域错误时会写 errno，引用 __errno()，newlib-nano 的
 *    libc 不提供该符号，需应用层给出。
 * _write 在 uart_retarget.c 中实现，此处不重复。
 */
#include <sys/stat.h>
#include <errno.h>

/* 链接脚本提供：_end（bss 末/堆起点）、_estack（RAM 顶） */
extern uint8_t _end;
extern uint8_t _estack;

/* newlib-nano 缺少的 errno 访问函数 */
static int s_errno;
int *__errno(void) { return &s_errno; }

static uint8_t *s_heap = NULL;

void *_sbrk(int incr)
{
    uint8_t *prev;
    if (s_heap == NULL) {
        s_heap = &_end;
    }
    prev = s_heap;
    /* 堆顶不得超过 栈顶 - 4KB 安全带 */
    if ((uint32_t)(s_heap + incr) > ((uint32_t)&_estack - 0x1000u)) {
        errno = ENOMEM;
        return (void *)-1;
    }
    s_heap += incr;
    return (void *)prev;
}

int _close(int fd)                       { (void)fd; return -1; }
int _fstat(int fd, struct stat *st)      { (void)fd; st->st_mode = S_IFCHR; return 0; }
int _isatty(int fd)                      { (void)fd; return 1; }
int _lseek(int fd, int off, int w)       { (void)fd; (void)off; (void)w; return 0; }
int _read(int fd, char *buf, int len)    { (void)fd; (void)buf; (void)len; return 0; }
void _exit(int status)                   { (void)status; while (1) { } }
int _kill(int pid, int sig)              { (void)pid; (void)sig; errno = EINVAL; return -1; }
int _getpid(void)                        { return 1; }
