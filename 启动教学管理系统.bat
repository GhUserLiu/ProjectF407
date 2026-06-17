@echo off
call conda activate stm32_teaching
cd /d C:\Users\liuzh\Projects\Workspace\stm32f407
python src\tools\teaching_management_gui\main.py
pause
