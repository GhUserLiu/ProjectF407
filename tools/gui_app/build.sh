#!/bin/bash
# STM32教学管理系统 - 打包脚本

set -e

echo "======================================"
echo "STM32教学管理系统 - 打包工具"
echo "======================================"
echo ""

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到Python"
    exit 1
fi

# 安装依赖
echo "正在安装依赖..."
pip install -r requirements.txt

# 清理旧版本
echo "正在清理旧版本..."
rm -rf build dist

# 执行打包
echo "正在打包应用..."
pyinstaller build.spec --clean --noconfirm

echo ""
echo "======================================"
echo "打包完成！"
echo "======================================"
echo ""
echo "可执行文件位置: dist/STM32教学管理系统.exe"
echo ""

# 检查打包结果
if [ -f "dist/STM32教学管理系统.exe" ]; then
    SIZE=$(du -h "dist/STM32教学管理系统.exe" | cut -f1)
    echo "文件大小: $SIZE"
    echo ""
    echo "可以尝试运行: dist/STM32教学管理系统.exe"
else
    echo "警告: 未找到生成的可执行文件"
fi
