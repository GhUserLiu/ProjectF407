#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生端 · 作业自检与自评系统 GUI 主入口
Main Entry Point for Student Self-Check & Self-Grade GUI

启动：PYTHONPATH=src python -m tools.student_submission_gui.main
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from tools.student_submission_gui.ui.main_window import MainWindow


def main():
    """主函数。"""
    # 必须在创建 QApplication 之前设置高 DPI 属性
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("学生端作业自检与自评")
    app.setOrganizationName("STM32F407 Teaching")

    # Windows 平台：设置进程 DPI 感知
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
