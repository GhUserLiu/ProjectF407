# -*- mode: python ; coding: utf-8 -*-
"""
学生端作业自检与自评系统 — PyInstaller 打包脚本
Student Self-Check & Self-Grade GUI — PyInstaller spec

构建：
    pyinstaller --noconfirm build_student.spec

产物：
    dist/StudentSelfCheck.exe          （单文件，windowed）

说明：
- 单文件（onefile）、无控制台（windowed）。启动时 PyInstaller 会解压到临时目录。
- 只读资源（rubric.json / config.yaml）随包打入，运行时由 runtime.bundle_root() 定位。
- 报告输出到用户主目录下的「STM32学生自检」（由 runtime.writable_root() 决定）。
- 显式排除学生端用不到的重型依赖（torch/sentence-transformers/pandas/sklearn/jieba 等），
  这些仅服务于教师端查重/语义检测，不在学生端运行时导入图中。
"""

block_cipher = None

a = Analysis(
    ['src/tools/student_submission_gui/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # (源路径, 打包内目标目录，相对于 bundle_root)
        ('data/rubrics/rubric.json', 'data/rubrics'),
        ('data/rubrics/rubric_enhanced.json', 'data/rubrics'),
        ('data/rubrics/final-project.json', 'data/rubrics'),
        ('data/config/teaching/config.yaml', 'data/config/teaching'),
    ],
    hiddenimports=[
        # 学生端运行时按需（惰性导入）加载的模块，显式声明以免漏打包
        'tools.plagiarism.grading.grading',
        'tools.plagiarism.image.image_counter',
        'tools.plagiarism.code_analysis.code_analyzer',
        # 运行时依赖（多数可自动发现，显式声明更稳）
        'defusedxml',
        'docx',
        'openpyxl',
        'PIL',
        'PIL._tkinter_finder',
        'numpy',
        # path_helper.load_experiments 在 try 内惰性 import yaml 解析 config.yaml；
        # 漏装会导致实验下拉回退到内置默认清单（缺期末综合项目）
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 学生端不需要的重型/无关依赖（防止 PyInstaller 静态分析误打包）
        'torch', 'torchvision', 'torchaudio',
        'sentence_transformers', 'transformers', 'tokenizers',
        'pandas', 'sklearn', 'scipy',
        'jieba',
        'matplotlib', 'IPython', 'jupyter', 'notebook',
        'pytest', '_pytest',
        'tkinter',
        'reportlab', 'markdown',
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
    name='StudentSelfCheck',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # 关闭 UPX：避免杀毒软件误报（代价是体积略大）
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,             # windowed GUI（无控制台窗口）
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
