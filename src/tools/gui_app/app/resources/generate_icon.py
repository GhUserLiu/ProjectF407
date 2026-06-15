#!/usr/bin/env python3
"""
生成 STM32 教学管理系统应用图标

使用 Pillow 绘制芯片风格的图标，包含：
- 芯片主体
- 引脚
- 电路纹路
- 教育元素
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size=(256, 256)):
    """创建图标图像"""
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w, h = size
    center_x, center_y = w // 2, h // 2

    # 颜色方案 - STM32 蓝色主题
    primary = (0, 82, 147)       # 深蓝
    secondary = (0, 124, 220)    # 亮蓝
    accent = (237, 28, 36)       # 红色点缀
    dark = (30, 30, 40)          # 深灰
    light = (200, 220, 240)      # 浅蓝灰

    # 芯片主体尺寸
    chip_size = int(min(w, h) * 0.55)
    chip_left = center_x - chip_size // 2
    chip_top = center_y - chip_size // 2
    chip_right = chip_left + chip_size
    chip_bottom = chip_top + chip_size

    # 引脚宽度和长度
    pin_width = max(2, size[0] // 64)
    pin_length = max(4, size[0] // 16)

    # 1. 绘制引脚 (上下左右各4个)
    pin_positions = []
    pins_per_side = 4
    pin_spacing = chip_size // (pins_per_side + 1)

    # 上方引脚
    for i in range(pins_per_side):
        x = chip_left + pin_spacing * (i + 1)
        y = chip_top - pin_length
        pin_positions.append((x, y, x + pin_width, chip_top))

    # 下方引脚
    for i in range(pins_per_side):
        x = chip_left + pin_spacing * (i + 1)
        y = chip_bottom
        pin_positions.append((x, y, x + pin_width, chip_bottom + pin_length))

    # 左侧引脚
    for i in range(pins_per_side):
        x = chip_left - pin_length
        y = chip_top + pin_spacing * (i + 1)
        pin_positions.append((x, y, chip_left, y + pin_width))

    # 右侧引脚
    for i in range(pins_per_side):
        x = chip_right
        y = chip_top + pin_spacing * (i + 1)
        pin_positions.append((x, y, chip_right + pin_length, y + pin_width))

    # 绘制所有引脚
    for pin in pin_positions:
        draw.rectangle(pin, fill=secondary)

    # 2. 绘制芯片主体背景 - 渐变效果
    for i in range(chip_size):
        alpha = int(255 * (1 - i / chip_size * 0.3))
        color = (*primary, alpha)
        draw.rectangle([chip_left, chip_top + i, chip_right, chip_top + i + 1], fill=color)

    # 重新绘制芯片边框
    draw.rectangle([chip_left, chip_top, chip_right, chip_bottom],
                  outline=secondary, width=max(1, size[0] // 128))

    # 内边框
    margin = max(2, size[0] // 64)
    draw.rectangle([chip_left + margin, chip_top + margin,
                   chip_right - margin, chip_bottom - margin],
                  outline=light, width=max(1, size[0] // 256))

    # 3. 绘制电路纹路
    circuit_margin = max(8, size[0] // 32)
    circuit_area = (chip_left + circuit_margin, chip_top + circuit_margin,
                   chip_right - circuit_margin, chip_bottom - circuit_margin)

    # 水平线
    line_width = max(1, size[0] // 128)
    for i in range(3):
        y = circuit_area[1] + (circuit_area[3] - circuit_area[1]) * (i + 1) // 4
        draw.line([circuit_area[0], y, circuit_area[2], y], fill=light, width=line_width)

    # 垂直线
    for i in range(3):
        x = circuit_area[0] + (circuit_area[2] - circuit_area[0]) * (i + 1) // 4
        draw.line([x, circuit_area[1], x, circuit_area[3]], fill=light, width=line_width)

    # 4. 绘制中心 MCU 标识圆圈
    circle_radius = size[0] // 8
    draw.ellipse([center_x - circle_radius, center_y - circle_radius,
                 center_x + circle_radius, center_y + circle_radius],
                outline=light, width=max(2, size[0] // 64))

    # 中心点
    dot_radius = max(2, size[0] // 64)
    draw.ellipse([center_x - dot_radius, center_y - dot_radius,
                 center_x + dot_radius, center_y + dot_radius], fill=accent)

    # 5. 绘制 STM32 文字 (如果尺寸允许)
    try:
        # 尝试使用系统字体
        font_size = max(8, size[0] // 16)
        font = ImageFont.truetype("arial.ttf", font_size)
        text = "STM32"
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = center_x - text_width // 2
        text_y = chip_bottom + pin_length + max(2, size[0] // 64)
        draw.text((text_x, text_y), text, font=font, fill=dark)
    except:
        pass  # 字体不可用，跳过文字

    return img

def create_ico(output_path="icon.ico"):
    """创建多尺寸 ICO 文件"""
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

    images = []
    for size in sizes:
        img = create_icon(size)
        images.append(img)

    # 保存为 ICO 文件
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images]
    )
    print(f"[OK] Icon generated: {output_path}")
    print(f"  Sizes: {', '.join(f'{s[0]}x{s[1]}' for s in sizes)}")

def create_png(output_path="icon.png"):
    """创建预览 PNG 文件"""
    img = create_icon((256, 256))
    img.save(output_path, 'PNG')
    print(f"[OK] PNG preview generated: {output_path}")

if __name__ == "__main__":
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate files
    ico_path = os.path.join(script_dir, "icon.ico")
    png_path = os.path.join(script_dir, "icon.png")

    print("Generating STM32 Teaching Manager icon...")
    create_ico(ico_path)
    create_png(png_path)
    print("\nIcon design details:")
    print("  - Dark blue chip body")
    print("  - 16 pins (4 per side)")
    print("  - Circuit pattern decoration")
    print("  - Center MCU identifier")
    print("  - STM32 text label")
