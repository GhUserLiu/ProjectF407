"""
STM32教学管理系统 - 主入口

启动GUI应用程序
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 添加项目根目录到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    # 可执行文件所在目录
    app_dir = Path(sys.executable).parent
    # 添加 tools 目录到路径（tools 目录在 app 的父级）
    # PyInstaller 会将 tools 作为数据文件放在根目录
    if (app_dir / 'tools').exists():
        sys.path.insert(0, str(app_dir))
    else:
        # 备用方案：添加内部路径
        sys.path.insert(0, str(Path(sys._MEIPASS) / 'tools'))
else:
    # 开发环境
    project_root = Path(__file__).parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.ui.main_window import MainWindow


def main():
    """主函数"""
    # 启用高DPI支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 创建应用实例
    app = QApplication(sys.argv)

    # 设置应用信息
    app.setApplicationName("STM32教学管理系统")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MCU Research")

    # 设置默认字体
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)

    # 设置样式
    app.setStyleSheet("""
        QMainWindow {
            background-color: #ffffff;
        }
        QWidget {
            background-color: #ffffff;
        }
    """)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    # 运行事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
