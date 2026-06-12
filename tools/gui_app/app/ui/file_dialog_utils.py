"""
文件对话框工具模块

提供文件对话框的智能定位功能
"""

from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import QFileDialog


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
        # 优先使用记忆的目录
        if cls._last_dirs.get(dir_type):
            memory_path = Path(cls._last_dirs[dir_type])
            if memory_path.exists():
                return str(memory_path)

        # 如果有项目配置，使用项目相关目录
        if config:
            if dir_type == 'submission' and hasattr(config, 'submission_dir'):
                if config.submission_dir and Path(config.submission_dir).exists():
                    return str(config.submission_dir)

            if dir_type == 'rubric' and hasattr(config, 'experiment_dir'):
                rubric_dir = Path(config.experiment_dir) / 'common' / 'rubrics'
                if rubric_dir.exists():
                    return str(rubric_dir)

            if dir_type in ('output', 'export') and hasattr(config, 'output_dir'):
                if config.output_dir and Path(config.output_dir).exists():
                    return str(config.output_dir)

            if hasattr(config, 'experiment_dir') and config.experiment_dir:
                if Path(config.experiment_dir).exists():
                    return str(config.experiment_dir)

        # 默认：使用当前工作目录
        return str(Path.cwd())

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
