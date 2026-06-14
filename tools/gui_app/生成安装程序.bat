@echo off
REM ====================================
REM STM32教学管理系统 - 生成安装程序
REM ====================================

setlocal enabledelayedexpansion

echo.
echo ====================================
REM STM32教学管理系统 - 生成安装程序
echo ====================================
echo.

REM 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo [1/2] 检查环境...
echo.

REM 检查 Inno Setup
where iscc >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Inno Setup！
    echo.
    echo 请先安装 Inno Setup:
    echo   下载地址: https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [OK] Inno Setup 已就绪

echo.
echo [2/2] 生成安装程序...
echo.

REM 运行 Inno Setup 编译器
iscc installer.iss

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 安装程序生成失败！
    pause
    exit /b 1
)

echo.
echo ====================================
echo 安装程序生成成功！
echo ====================================
echo.

REM 检查输出文件
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
    echo [警告] 未找到生成的安装程序
    echo.
    pause
)

endlocal
