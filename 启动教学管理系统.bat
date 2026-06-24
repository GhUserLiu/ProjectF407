@echo off
REM 以本 bat 所在目录（仓库根）为工作目录，便于整仓库迁移后仍可直接运行
cd /d "%~dp0"
call conda activate stm32_teaching
python src\tools\teaching_management_gui\main.py
pause
