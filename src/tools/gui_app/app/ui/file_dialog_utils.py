"""
文件对话框工具模块

提供文件对话框的智能定位功能
"""

import os
import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtCore import QSettings


class DialogStartDir:
    """对话框起始目录管理"""

    # 记忆最后使用的目录
    _last_dirs = {
        'project': None,      # 项目配置
        'submission': None,    # 提交目录
        'rubric': None,        # 评分标准
        'output': None,        # 输出目录
        'export': None,        # 导出目录
    }

    # 安装目录缓存
    _install_dir = None
    _data_dir = None

    @classmethod
    def _get_install_dir(cls) -> Optional[Path]:
        """
        获取安装目录

        优先级:
        1. 检查 PyInstaller 临时目录（打包后的数据）
        2. 检查可执行文件所在目录
        3. 从注册表读取 (Windows)
        4. 检查 Program Files 中的安装目录
        """
        if cls._install_dir:
            return cls._install_dir

        try:
            # 1. 优先检查 PyInstaller 临时目录（打包后的数据在这里）
            if getattr(sys, 'frozen', False):
                # 运行打包后的 exe
                meipass_str = getattr(sys, '_MEIPASS', None)
                if meipass_str:
                    meipass = Path(meipass_str)
                    # 检查 meipass 中的 data 目录
                    data_dir = meipass / 'data'
                    if data_dir.exists():
                        cls._install_dir = meipass
                        cls._data_dir = data_dir
                        return cls._install_dir
                else:
                    # 如果没有 _MEIPASS，使用 exe 目录
                    exe_dir = Path(sys.executable).parent
                    data_dir = exe_dir / 'data'
                    if data_dir.exists():
                        cls._install_dir = exe_dir
                        cls._data_dir = data_dir
                        return cls._install_dir
                    cls._install_dir = exe_dir
                    return cls._install_dir
            else:
                # 运行开发环境
                # 从 file_dialog_utils.py 往上找项目根目录
                # file_dialog_utils.py 在 tools/gui_app/app/ui/ 下
                # 项目根目录应该是 tools 的父目录
                try:
                    current = Path(__file__).resolve()
                    # 往上查找，直到找到包含 Makefile 或 docs/teaching 的目录
                    while current:
                        # 检查是否是项目根目录（包含 Makefile 或 docs/teaching）
                        if (current / 'Makefile').exists() or (current / 'docs' / 'teaching').exists():
                            exe_dir = current
                            break
                        parent = current.parent
                        if parent == current:  # 到达根目录
                            exe_dir = Path.cwd()
                            break
                        current = parent
                except:
                    exe_dir = Path.cwd()

            # 检查是否存在 data 目录
            data_dir = exe_dir / 'data'
            if data_dir.exists():
                cls._install_dir = exe_dir
                cls._data_dir = data_dir
                return cls._install_dir

            # 如果 exe 目录没有 data，至少返回 exe 目录
            if exe_dir.exists():
                cls._install_dir = exe_dir
                return cls._install_dir

            # 2. 尝试从注册表读取 (Windows) - 添加更安全的错误处理
            if sys.platform == 'win32':
                try:
                    import winreg
                    key_path = r'Software\STM32教学管理系统'
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path, 0, winreg.KEY_READ)
                    install_path = winreg.QueryValueEx(key, 'InstallPath')[0]
                    winreg.CloseKey(key)

                    install_path_obj = Path(install_path)
                    if install_path_obj.exists():
                        cls._install_dir = install_path_obj
                        return cls._install_dir
                except Exception:
                    # 注册表读取失败，继续尝试其他方法
                    pass

            # 3. 检查 Program Files 中的安装目录 (Windows)
            if sys.platform == 'win32':
                program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
                install_path = Path(program_files) / 'STM32教学管理系统'
                if install_path.exists():
                    cls._install_dir = install_path
                    cls._data_dir = install_path / 'data'
                    return cls._install_dir

            # 4. 检查 Program Files (x86)
            if sys.platform == 'win32':
                program_files_x86 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
                install_path = Path(program_files_x86) / 'STM32教学管理系统'
                if install_path.exists():
                    cls._install_dir = install_path
                    cls._data_dir = install_path / 'data'
                    return cls._install_dir
        except Exception as e:
            print(f"[ERROR] Error in _get_install_dir: {e}", file=sys.stderr)

        return None

    @classmethod
    def _get_data_dir(cls) -> Optional[Path]:
        """获取数据目录"""
        if cls._data_dir:
            return cls._data_dir

        install_dir = cls._get_install_dir()
        if install_dir:
            data_dir = install_dir / 'data'
            if data_dir.exists():
                cls._data_dir = data_dir
                return data_dir

        return None

    @classmethod
    def get_start_dir(cls, dir_type: str, config=None) -> str:
        """
        获取对话框的起始目录

        Args:
            dir_type: 目录类型 ('project', 'submission', 'rubric', 'output', 'export')
            config: 项目配置对象

        Returns:
            起始目录路径字符串
        """
        try:
            # 优先使用记忆的目录
            if cls._last_dirs.get(dir_type):
                memory_path = Path(cls._last_dirs[dir_type])
                if memory_path.exists():
                    return str(memory_path)

            # 获取安装目录下的 data 文件夹
            data_dir = cls._get_data_dir()

            # 如果有项目配置，使用项目相关目录
            if config:
                if dir_type == 'submission' and hasattr(config, 'submission_dir'):
                    if config.submission_dir and Path(config.submission_dir).exists():
                        return str(config.submission_dir)

                if dir_type == 'rubric':
                    # 优先使用安装目录下的 rubrics
                    if data_dir:
                        rubric_dir = data_dir / 'rubrics'
                        if rubric_dir.exists():
                            return str(rubric_dir)
                    # 其次使用项目配置中的 rubrics
                    if hasattr(config, 'experiment_dir'):
                        rubric_dir = Path(config.experiment_dir) / 'common' / 'rubrics'
                        if rubric_dir.exists():
                            return str(rubric_dir)

                if dir_type in ('output', 'export') and hasattr(config, 'output_dir'):
                    if config.output_dir and Path(config.output_dir).exists():
                        return str(config.output_dir)

                if dir_type == 'template':
                    # 优先使用安装目录下的 templates
                    if data_dir:
                        template_dir = data_dir / 'templates'
                        if template_dir.exists():
                            return str(template_dir)

                if hasattr(config, 'experiment_dir') and config.experiment_dir:
                    if Path(config.experiment_dir).exists():
                        return str(config.experiment_dir)

            # 根据类型使用安装目录下的默认路径
            if data_dir:
                # 优先检查主数据目录，然后检查测试数据目录
                check_dirs = [data_dir, data_dir / 'test']

                if dir_type == 'rubric':
                    for base_dir in check_dirs:
                        rubric_dir = base_dir / 'rubrics'
                        if rubric_dir.exists():
                            # 检查是否有文件（使用 listdir 而不是 iterdir，更可靠）
                            try:
                                if list(rubric_dir.iterdir()):
                                    return str(rubric_dir)
                            except Exception:
                                pass

                if dir_type == 'template':
                    for base_dir in check_dirs:
                        template_dir = base_dir / 'templates'
                        if template_dir.exists():
                            try:
                                if list(template_dir.iterdir()):
                                    return str(template_dir)
                            except Exception:
                                pass

                if dir_type == 'submission':
                    for base_dir in check_dirs:
                        sub_dir = base_dir / 'submissions'
                        if sub_dir.exists():
                            try:
                                if list(sub_dir.iterdir()):
                                    return str(sub_dir)
                            except Exception:
                                pass

                    # 特殊处理：students目录（用于多班级视图）
                    for base_dir in check_dirs:
                        students_dir = base_dir / 'students'
                        if students_dir.exists():
                            try:
                                if list(students_dir.iterdir()):
                                    return str(students_dir)
                            except Exception:
                                pass

                if dir_type in ('output', 'export'):
                    for base_dir in check_dirs:
                        output_dir = base_dir / 'results'
                        if output_dir.exists():
                            return str(output_dir)

                # 如果以上都失败，返回 data 目录本身作为最后回退
                if data_dir.exists():
                    return str(data_dir)

            # 默认：使用当前工作目录
            cwd = Path.cwd()
            if cwd.exists():
                return str(cwd)

            # 最后的回退：用户主目录
            return str(Path.home())

        except Exception as e:
            # 发生任何错误时，回退到用户主目录
            print(f"Warning: Error getting start dir: {e}")
            return str(Path.home())

    @classmethod
    def remember_dir(cls, dir_type: str, dir_path: str):
        """
        记住最后使用的目录

        Args:
            dir_type: 目录类型
            dir_path: 目录路径
        """
        if dir_path:
            path = Path(dir_path)
            if path.exists() and path.is_dir():
                cls._last_dirs[dir_type] = str(path)
            elif path.parent.exists():
                cls._last_dirs[dir_type] = str(path.parent)


def get_open_filename(
    parent,
    title: str,
    filter: str,
    dir_type: str,
    config=None
) -> tuple[str, str]:
    """
    打开文件对话框（带智能定位）

    Args:
        parent: 父窗口
        title: 对话框标题
        filter: 文件过滤器
        dir_type: 目录类型
        config: 项目配置

    Returns:
        (文件路径, 选中的过滤器)
    """
    start_dir = DialogStartDir.get_start_dir(dir_type, config)
    file_path, selected_filter = QFileDialog.getOpenFileName(
        parent, title, start_dir, filter
    )
    if file_path:
        DialogStartDir.remember_dir(dir_type, file_path)
    return file_path, selected_filter


def get_save_filename(
    parent,
    title: str,
    filter: str,
    dir_type: str,
    config=None,
    default_name: str = ""
) -> tuple[str, str]:
    """
    保存文件对话框（带智能定位）

    Args:
        parent: 父窗口
        title: 对话框标题
        filter: 文件过滤器
        dir_type: 目录类型
        config: 项目配置
        default_name: 默认文件名

    Returns:
        (文件路径, 选中的过滤器)
    """
    start_dir = DialogStartDir.get_start_dir(dir_type, config)
    if default_name:
        start_dir = str(Path(start_dir) / default_name)
    file_path, selected_filter = QFileDialog.getSaveFileName(
        parent, title, start_dir, filter
    )
    if file_path:
        DialogStartDir.remember_dir(dir_type, file_path)
    return file_path, selected_filter


def get_existing_directory(
    parent,
    title: str,
    dir_type: str,
    config=None
) -> str:
    """
    选择目录对话框（带智能定位）

    Args:
        parent: 父窗口
        title: 对话框标题
        dir_type: 目录类型
        config: 项目配置

    Returns:
        选择的目录路径，空字符串表示取消
    """
    start_dir = DialogStartDir.get_start_dir(dir_type, config)
    dir_path = QFileDialog.getExistingDirectory(parent, title, start_dir)
    if dir_path:
        DialogStartDir.remember_dir(dir_type, dir_path)
    return dir_path
