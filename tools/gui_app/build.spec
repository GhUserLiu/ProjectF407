# -*- mode: python ; coding: utf-8 -*-
"""
STM32教学管理系统 - PyInstaller打包配置

使用方法:
    pyinstaller build.spec --clean --noconfirm
"""

import sys
import os
from pathlib import Path

# 当前spec文件所在目录（gui_app目录）
spec_dir = Path(SPECPATH).absolute()

# 项目根目录
project_root = spec_dir.parents[2]

# 数据文件目录
docs_dir = project_root / "docs" / "teaching" / "common"
tools_dir = project_root / "tools"
plagiarism_dir = tools_dir / "plagiarism"
templates_dir = tools_dir / "templates"

# 检查目录是否存在
datas = []

# 包含文档和配置文件
if docs_dir.exists():
    datas.append((str(docs_dir), 'docs/teaching/common'))

# 包含plagiarism目录
if plagiarism_dir.exists():
    for item in plagiarism_dir.rglob('*'):
        if item.is_file():
            rel_path = item.relative_to(plagiarism_dir)
            datas.append((str(item), f'tools/plagiarism/{rel_path.parent}'))

# 包含templates目录
if templates_dir.exists():
    for item in templates_dir.rglob('*'):
        if item.is_file():
            rel_path = item.relative_to(templates_dir)
            datas.append((str(item), f'tools/templates/{rel_path.parent}'))

# 包含核心tools文件
for py_file in ['submission_utils.py', 'enhanced_quality_assessment.py',
                'plagiarism_detection_enhanced.py', 'generate_grading_excel.py']:
    file_path = tools_dir / py_file
    if file_path.exists():
        datas.append((str(file_path), 'tools'))

# 包含app目录本身
app_dir = spec_dir / "app"
if app_dir.exists():
    for item in app_dir.rglob('*.py'):
        if item.is_file():
            rel_path = item.relative_to(app_dir)
            datas.append((str(item), f'app/{rel_path.parent}'))

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(spec_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # PyQt6
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # 数据处理
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        # 文档处理
        'docx',
        'docx.text',
        'docx.table',
        # 中文处理
        'jieba',
        'jieba.analyse',
        # 机器学习
        'sklearn',
        'sklearn.utils',
        'sklearn.feature_extraction.text',
        # numpy
        'numpy',
        # 报告生成
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        # 工具
        'python_dateutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块以减小体积
        'matplotlib',
        'scipy',
        'IPython',
        'pytest',
        'pandas',
        'PyQt6.QtWebEngineWidgets',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='STM32教学管理系统',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 设为True以便查看调试信息
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
