@echo off
REM ============================================================
REM 学生端作业自检与自评系统 — 打包脚本（Windows）
REM Student Self-Check & Self-Grade GUI — build script
REM
REM 用法：在仓库根目录执行  scripts\build_student_exe.bat
REM 产物：dist\StudentSelfCheck.exe（单文件，无控制台）
REM
REM 关键点：
REM   - 使用独立的干净虚拟环境打包，固定 numpy<2。
REM     conda/系统环境的 numpy 2.x 与 PyInstaller 不兼容
REM     （RuntimeError: CPU dispatcher tracer already initialized）。
REM   - 学生端运行时只需 numpy/PIL/docx/openpyxl/defusedxml，
REM     不含 torch/pandas/sklearn 等重型依赖（显式排除）。
REM ============================================================
setlocal

set VENV=%USERPROFILE%\stm32f407_buildvenv
set REPO=%~dp0..

if not exist "%VENV%\Scripts\python.exe" (
  echo [1/3] 创建干净构建虚拟环境： %VENV%
  python -m venv "%VENV%"
  "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
  echo [2/3] 安装最小依赖（numpy^<2）...
  "%VENV%\Scripts\python.exe" -m pip install ^
    PyQt6 defusedxml python-docx openpyxl Pillow "numpy<2" PyYAML PyInstaller
) else (
  echo [1/3] 复用已有虚拟环境： %VENV%
  echo [2/3] 跳过依赖安装
)

pushd "%REPO%"
echo [3/3] 清理旧产物并打包 ...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%VENV%\Scripts\python.exe" -m PyInstaller --noconfirm build_student.spec
popd

echo.
if exist "%REPO%\dist\StudentSelfCheck.exe" (
  echo === 完成 ===
  echo   产物：%REPO%\dist\StudentSelfCheck.exe
  echo   运行后报告输出到：%%USERPROFILE%%\STM32学生自检\outputs\student_self_check\
) else (
  echo === 打包失败，请检查上方日志 ===
  exit /b 1
)
endlocal
