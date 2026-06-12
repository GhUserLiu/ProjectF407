# -*- mode: python ; coding: utf-8 -*-
"""
STM32教学管理系统 - PyInstaller打包配置

使用方法:
    # 单文件模式 (默认)
    pyinstaller build.spec --clean --noconfirm

    # 目录模式 (启动更快)
    pyinstaller build.spec --clean --noconfirm --onefile-mode=false
"""

import sys
import os
from pathlib import Path

# === 打包模式配置 ===
# True = 单文件 exe (体积小，分发方便，启动慢)
# False = 目录模式 (启动快，体积大)
ONEFILE_MODE = '--onefile-mode=false' not in sys.argv

# 版本信息文件
version_file = spec_dir / 'app' / 'resources' / 'version.txt'

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

# 包含plagiarism目录（简化处理，只包含必要的文件）
# 注意：由于导入已经变为可选，这里可以省略详细打包

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

# 包含security模块（安全工具集）
security_dir = tools_dir / "security"
if security_dir.exists():
    for item in security_dir.rglob('*.py'):
        if item.is_file():
            rel_path = item.relative_to(security_dir)
            datas.append((str(item), f'tools/security/{rel_path.parent}'))

# 包含配置文件
config_files = ['security_config.json']
for cfg in config_files:
    cfg_path = tools_dir / cfg
    if cfg_path.exists():
        datas.append((str(cfg_path), 'tools'))

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
    pathex=[str(spec_dir), str(project_root)],  # 添加项目根目录到路径
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
        'openpyxl.formula',
        'openpyxl.writer',
        # 文档处理
        'docx',
        'docx.text',
        'docx.table',
        'docx.oxml',
        'docx.opc',
        # 中文处理
        'jieba',
        'jieba.analyse',
        'jieba.posseg',
        # 机器学习 (scikit-learn)
        'sklearn',
        'sklearn.utils',
        'sklearn.feature_extraction.text',
        'sklearn.metrics.pairwise',
        'sklearn.feature_extraction',
        # numpy
        'numpy',
        # 报告生成
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.pdfbase',
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        # 工具
        'python_dateutil',
        'dateutil',
        'dateutil.parser',
        # 可选语义检测模块 (如果安装了)
        'sentence_transformers',
        'transformers',
        'torch',
        # HTML 处理
        'markdown',
        'markdown.extensions',
        # XML 解析 (安全工具需要)
        'defusedxml',
        'defusedxml.ElementTree',
        'xml.etree.ElementTree',
        # ZIP 处理
        'zipfile',
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

if ONEFILE_MODE:
    # === 单文件模式 ===
    # 所有文件打包到一个 exe 中，分发方便但启动慢
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
        console=False,  # GUI应用，不需要控制台窗口
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        # 图标文件
        icon=str(spec_dir / 'app' / 'resources' / 'icon.ico') if (spec_dir / 'app' / 'resources' / 'icon.ico').exists() else None,
        # 版本信息
        version=str(version_file) if version_file.exists() else None,
    )
else:
    # === 目录模式 ===
    # 文件放在目录中，启动快，体积大
    exe = EXE(
        pyz,
        a.scripts,
        [],  # 不包含 binaries 和 datas
        exclude_binaries=True,
        name='STM32教学管理系统',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(spec_dir / 'app' / 'resources' / 'icon.ico') if (spec_dir / 'app' / 'resources' / 'icon.ico').exists() else None,
        version=str(version_file) if version_file.exists() else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='STM32教学管理系统',
    )
