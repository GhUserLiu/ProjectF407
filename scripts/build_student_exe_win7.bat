@echo off
REM ============================================================
REM 学生端作业自检与自评系统 — Windows 7 兼容版打包脚本
REM Student Self-Check & Self-Grade GUI — Win7-compatible build (conda)
REM
REM 用法：在仓库根目录执行  scripts\build_student_exe_win7.bat
REM 产物：dist\StudentSelfCheck_Win7.exe（单文件，无控制台，覆盖 Win7/8.1/10/11）
REM
REM 关键点：
REM   - 用独立 conda 环境 stm32f407-win7（Python 3.8 + PyQt5==5.15.2）打包，
REM     不污染 base / 其它环境，也不与 PyQt6 的 StudentSelfCheck.exe 冲突。
REM   - 版本锁定面向 Windows 7 兼容：
REM       PyQt5==5.15.2  （Qt 5.15.2 = 最后一个官方支持 Win7 的 Qt）
REM       numpy==1.24.4  （1.25+ 需 Python 3.9）
REM       Pillow==10.4.0 （11.0+ 需 Python 3.9）
REM     教师端查重/语义所需的重型依赖（torch/pandas/sklearn/jieba）显式排除。
REM   - 清理仅删除 build\ 与旧 Win7 产物，保留 dist\StudentSelfCheck.exe（PyQt6 版）。
REM ============================================================
setlocal enabledelayedexpansion

set ENV=stm32f407-win7
set PY=3.8
set REPO=%~dp0..

where conda >nul 2>&1
if errorlevel 1 (
  echo [错误] 未找到 conda。请先安装 Miniconda/Anaconda 并确保 conda 在 PATH。
  exit /b 1
)

REM [1/4] 创建 conda 环境（若不存在）
conda env list | findstr /B /C:"%ENV% " >nul
if errorlevel 1 (
  echo [1/4] 创建 conda 环境 %ENV% ^(python=%PY%^) ...
  call conda create -n %ENV% python=%PY% -y
  if errorlevel 1 ( echo [错误] 创建 conda 环境失败。& exit /b 1 )
) else (
  echo [1/4] 复用已有 conda 环境：%ENV%
)

REM [2/4] 激活
call conda activate %ENV%
if errorlevel 1 (
  echo [错误] 激活失败。若未对 cmd 初始化，请先执行：  conda init cmd.exe
  exit /b 1
)

REM [3/4] 安装 Windows 7 兼容依赖
echo [3/4] 安装 Win7 兼容依赖 ...
python -m pip install --upgrade pip
python -m pip install ^
  "PyQt5==5.15.2" ^
  "numpy==1.24.4" "Pillow==10.4.0" ^
  "python-docx==1.1.2" "openpyxl==3.1.5" ^
  "defusedxml==0.7.1" "PyYAML==6.0.2" ^
  "pyinstaller==6.21.0"
if errorlevel 1 ( echo [错误] 依赖安装失败。& exit /b 1 )

REM [4/4] 打包
pushd "%REPO%"
echo [4/4] 清理旧产物并打包 ...
if exist build\StudentSelfCheck_Win7 rmdir /s /q build\StudentSelfCheck_Win7
if exist dist\StudentSelfCheck_Win7.exe del /q dist\StudentSelfCheck_Win7.exe
python -m PyInstaller --noconfirm build_student_win7.spec
set RC=%ERRORLEVEL%
popd

call conda deactivate

echo.
if exist "%REPO%\dist\StudentSelfCheck_Win7.exe" (
  echo === 完成 ===
  echo   Win7 兼容产物：%REPO%\dist\StudentSelfCheck_Win7.exe
  echo   覆盖系统：Windows 7 / 8.1 / 10 / 11
  echo   运行后报告输出到：%%USERPROFILE%%\STM32学生自检\outputs\student_self_check\
) else (
  echo === 打包失败（退出码 !RC!），请检查上方日志 ===
  exit /b 1
)
endlocal
