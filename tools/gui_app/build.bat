@echo off
REM STM32教学管理系统 - Windows打包脚本

echo ======================================
echo STM32教学管理系统 - 打包工具
echo ======================================
echo.

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)

REM 安装依赖
echo 正在安装依赖...
pip install -r requirements.txt

REM 清理旧版本
echo 正在清理旧版本...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 执行打包
echo 正在打包应用...
pyinstaller build.spec --clean --noconfirm

echo.
echo ======================================
echo 打包完成！
echo ======================================
echo.
echo 可执行文件位置: dist\STM32教学管理系统.exe
echo.

REM 检查打包结果
if exist "dist\STM32教学管理系统.exe" (
    echo 打包成功！
) else (
    echo 警告: 未找到生成的可执行文件
)

pause
