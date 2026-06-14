"""
STM32教学管理系统 - 主入口

启动GUI应用程序
"""

import sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 添加项目根目录到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件
    # PyInstaller 会将所有打包的文件放在 sys._MEIPASS 目录中
    # 我们需要将这个目录添加到 sys.path 中，这样 Python 才能找到所有模块
    meipass = Path(sys._MEIPASS)
    sys.path.insert(0, str(meipass))

    # 另外，如果 tools 作为数据文件被打包，也需要确保其可被导入
    if (meipass / 'tools').exists():
        # 将 tools 父目录添加到路径
        sys.path.insert(0, str(meipass))
else:
    # 开发环境
    project_root = Path(__file__).parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.ui.main_window import MainWindow


def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(f"[FATAL ERROR] Unhandled exception:\n{error_msg}", file=sys.stderr)

    # 尝试显示错误对话框
    try:
        QMessageBox.critical(
            None,
            "程序错误",
            f"发生未捕获的异常:\n\n{exc_type.__name__}: {exc_value}\n\n详细信息已输出到控制台。"
        )
    except:
        pass


# 设置全局异常处理
sys.excepthook = handle_exception


def main():
    """主函数"""
    try:
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
    except Exception as e:
        error_msg = f"启动程序时发生错误:\n{str(e)}\n\n{traceback.format_exc()}"
        print(f"[FATAL ERROR] {error_msg}", file=sys.stderr)
        try:
            QMessageBox.critical(None, "启动失败", error_msg)
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
