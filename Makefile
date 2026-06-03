# Makefile for STM32F407 Projects
# Usage: make PROJECT=01-turn-signal

# Toolchain
PREFIX = arm-none-eabi-
CC = $(PREFIX)gcc
AS = $(PREFIX)as
LD = $(PREFIX)ld
OBJCOPY = $(PREFIX)objcopy

# Default project
PROJECT ?= 01-turn-signal

# Directories
PROJECT_DIR = projects/$(PROJECT)
COMMON_DIR = common
BUILD_DIR = build/$(PROJECT)/Debug

# Source files
# 如果存在 main_interrupt.c，使用中断版本；否则使用普通 main.c
ifeq ($(wildcard $(PROJECT_DIR)/main_interrupt.c),)
    C_SOURCES = $(PROJECT_DIR)/main.c \
                $(COMMON_DIR)/hal/stm32f4xx_hal.c
else
    C_SOURCES = $(PROJECT_DIR)/main_interrupt.c \
                $(COMMON_DIR)/hal/stm32f4xx_hal.c \
                $(COMMON_DIR)/hal/stm32f4xx_hal_ext.c
endif

ASM_SOURCES = $(COMMON_DIR)/startup_stm32f407xx.s

# Linker script
LDSCRIPT = STM32F407XX_FLASH.ld

# Include paths
CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
CFLAGS += -Wall -Wextra -O0 -g3
CFLAGS += -DSTM32F407xx
CFLAGS += -I$(PROJECT_DIR) -I$(COMMON_DIR)/inc -I$(COMMON_DIR)/hal

# Linker flags
LDFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
LDFLAGS += -T$(LDSCRIPT) -specs=nano.specs -lc -lm -nostartfiles
LDFLAGS += -Wl,-Map=$(BUILD_DIR)/$(PROJECT).map

# Object files
ifeq ($(wildcard $(PROJECT_DIR)/main_interrupt.c),)
    MAIN_OBJ = $(BUILD_DIR)/main.o
    HAL_EXT_OBJ =
else
    MAIN_OBJ = $(BUILD_DIR)/main_interrupt.o
    HAL_EXT_OBJ = $(BUILD_DIR)/stm32f4xx_hal_ext.o
endif

OBJECTS = $(MAIN_OBJ) \
          $(BUILD_DIR)/stm32f4xx_hal.o \
          $(HAL_EXT_OBJ) \
          $(BUILD_DIR)/startup_stm32f407xx.o

# Output files (以项目名称命名)
ELF = $(BUILD_DIR)/$(PROJECT).elf
HEX = $(BUILD_DIR)/$(PROJECT).hex
BIN = $(BUILD_DIR)/$(PROJECT).bin

.PHONY: all clean

all: $(HEX)

$(HEX): $(ELF)
	@echo "Creating HEX file..."
	$(OBJCOPY) -O ihex $< $@
	@echo "HEX file created: $@"

$(BIN): $(ELF)
	@echo "Creating BIN file..."
	$(OBJCOPY) -O binary $< $@

$(ELF): $(OBJECTS)
	@echo "Linking..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(LDFLAGS) $(OBJECTS) -o $@

$(BUILD_DIR)/main.o: $(PROJECT_DIR)/main.c
	@echo "Compiling $<..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/main_interrupt.o: $(PROJECT_DIR)/main_interrupt.c
	@echo "Compiling $<..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/stm32f4xx_hal_ext.o: $(COMMON_DIR)/hal/stm32f4xx_hal_ext.c
	@echo "Compiling $<..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/stm32f4xx_hal.o: $(COMMON_DIR)/hal/stm32f4xx_hal.c
	@echo "Compiling $<..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup_stm32f407xx.o: $(COMMON_DIR)/startup_stm32f407xx.s
	@echo "Assembling $<..."
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf build/

list:
	@echo "Available projects:"
	@ls -1 projects/
