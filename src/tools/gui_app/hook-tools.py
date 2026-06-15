"""
PyInstaller hook for tools package
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# 收集 tools 包的所有子模块
hiddenimports = collect_submodules('tools')

# 收集 tools 包的数据文件
datas = collect_data_files('tools', include_py_files=True)
