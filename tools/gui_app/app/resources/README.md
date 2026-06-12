# 应用图标说明

## 图标规格

- **文件名**: `icon.ico`
- **尺寸**: 至少包含 16x16, 32x32, 48x48, 256x256 四种尺寸
- **格式**: Windows ICO 格式

## 获取图标的方式

### 方式1: 使用在线工具
1. 访问 [favicon.io](https://favicon.io/) 或类似网站
2. 上传 PNG 图片或使用文字生成
3. 下载生成的 .ico 文件，重命名为 `icon.ico` 放到此目录

### 方式2: 使用 ImageMagick 转换
```bash
# 如果有 PNG 图标
magick convert icon.png -define icon:auto-resize=256,48,32,16 icon.ico
```

### 方式3: 使用 Pillow (Python)
```python
from PIL import Image

img = Image.open('icon.png')
sizes = [(16, 16), (32, 32), (48, 48), (256, 256)]
img.save('icon.ico', format='ICO', sizes=sizes)
```

## 图标设计建议

- 芯片或 MCU 图标
- STM32 或 ARM 标志
- 齿轮/设置图标（代表工具）
- 简洁的单色设计
