@echo off
REM ====================================
REM STM32教学管理系统 - 完整构建脚本
REM ====================================
REM 此脚本将执行以下操作：
REM 1. 生成测试数据
REM 2. 使用 PyInstaller 打包程序
REM 3. 使用 Inno Setup 生成安装程序
REM ====================================

setlocal enabledelayedexpansion

echo.
echo ====================================
echo STM32教学管理系统 - 完整构建流程
echo ====================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM ==================== 检查环境 ====================
echo [1/5] 检查构建环境...
echo.

REM 检查 Python
python --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python！
    echo 请先安装 Python 3.8 或更高版本。
    pause
    exit /b 1
)
echo [OK] Python 已安装

REM 检查 PyInstaller
python -c "import PyInstaller" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [安装] 正在安装 PyInstaller...
    pip install pyinstaller
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] PyInstaller 安装失败！
        pause
        exit /b 1
    )
)
echo [OK] PyInstaller 已就绪

REM 检查 Inno Setup
where iscc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [警告] Inno Setup 未找到！
    echo.
    echo 安装程序生成将被跳过。
    echo 请先安装 Inno Setup:
    echo   下载地址: https://jrsoftware.org/isdl.php
    echo.
    set NO_ISCC=1
) else (
    echo [OK] Inno Setup 已就绪
)

echo.
echo ==================== 生成测试数据 ====================
echo [2/5] 生成测试数据...
python create_test_data.py
if %ERRORLEVEL% NEQ 0 (
    echo [警告] 测试数据生成失败，继续...
) else (
    echo [OK] 测试数据生成完成
)

echo.
echo ==================== 清理旧文件 ====================
echo [3/5] 清理旧的构建文件...

REM 清理 PyInstaller 输出
if exist "build" (
    rmdir /s /q "build" 2>nul
)
if exist "dist" (
    rmdir /s /q "dist" 2>nul
)
if exist "spec" (
    rmdir /s /q "spec" 2>nul
)

echo [OK] 旧文件已清理

echo.
echo ==================== 打包应用程序 ====================
echo [4/5] 使用 PyInstaller 打包...
echo.

REM 选择打包模式：默认为单文件模式
REM 如果需要目录模式，请取消下面的注释
REM set PYINSTALLER_MODE=--onedir
set PYINSTALLER_MODE=

python -m PyInstaller build.spec --clean --noconfirm %PYINSTALLER_MODE%
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] PyInstaller 打包失败！
    pause
    exit /b 1
)

REM 检查输出文件
if exist "dist\STM32教学管理系统.exe" (
    echo [OK] 单文件模式打包成功: dist\STM32教学管理系统.exe
) else if exist "dist\STM32教学管理系统\STM32教学管理系统.exe" (
    echo [OK] 目录模式打包成功: dist\STM32教学管理系统\
    set PYINSTALLER_MODE=--onedir
) else (
    echo [错误] 未找到输出文件！
    pause
    exit /b 1
)

echo.
echo ==================== 生成安装程序 ====================
echo [5/5] 生成安装程序...

if defined NO_ISCC (
    echo [跳过] Inno Setup 未安装，跳过安装程序生成。
    echo.
    echo 构建完成！
    echo 可执行文件位置: dist\
    goto :end
)

iscc installer.iss
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 安装程序生成失败！
    pause
    exit /b 1
)

echo [OK] 安装程序生成成功！

:end
echo.
echo ====================================
echo 构建完成！
echo ====================================
echo.

if exist "installer_output\STM32教学管理系统_v2.6.0_安装程序.exe" (
    echo 安装程序位置:
    echo   installer_output\STM32教学管理系统_v2.6.0_安装程序.exe
    echo.

    REM 计算文件大小
    for %%A in ("installer_output\STM32教学管理系统_v2.6.0_安装程序.exe") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE! / 1048576
    )
    echo 文件大小: !SIZE_MB! MB
    echo.

    echo 按任意键打开输出文件夹...
    pause >nul
    explorer installer_output
) else (
    echo 可执行文件位置: dist\
    echo.
    pause
)

endlocal
