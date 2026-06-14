# -*- mode: python ; coding: utf-8 -*-
"""
STM32教学管理系统 - PyInstaller打包配置

使用方法:
    # 单文件模式 (默认)
    pyinstaller build.spec --clean --noconfirm

    # 目录模式 (启动更快)
    pyinstaller build.spec --clean --noconfirm --onedir
"""

import sys
import os
import shutil
from pathlib import Path

# === 打包模式配置 ===
# True = 单文件 exe (体积小，分发方便，启动慢)
# False = 目录模式 (启动快，体积大)
ONEDIR_MODE = True  # '--onedir' in sys.argv

# 是否包含测试工具（临时启用用于调试）
INCLUDE_TEST_TOOL = False  # os.environ.get('INCLUDE_TEST_TOOL', '0') == '1'

# 当前spec文件所在目录（gui_app目录）
spec_dir = Path(SPECPATH).absolute()

# 版本信息文件
version_file = spec_dir / 'app' / 'resources' / 'version.txt'
icon_file = spec_dir / 'app' / 'resources' / 'icon.ico'

# 项目根目录 - 修正路径计算
# spec_dir 是 tools/gui_app，需要往上 1 级到达项目根目录
project_root = None
for i in range(5):
    if i >= len(spec_dir.parents):
        break
    candidate = spec_dir.parents[i]
    # 检查是否是项目根目录（包含 Makefile 或 tools/__init__.py）
    if (candidate / 'Makefile').exists() or (candidate / 'tools' / '__init__.py').exists():
        project_root = candidate
        break

# 如果找不到，回退到 parents[1]（通常是项目根目录）
if not project_root:
    project_root = spec_dir.parents[1]

# 数据文件目录
docs_dir = project_root / "docs" / "teaching" / "common"
tools_dir = project_root / "tools"
templates_dir = tools_dir / "templates"
security_dir = tools_dir / "security"

# 收集所有需要打包的数据文件
datas = []
binaries = []

def add_directory_contents(src_dir: Path, dst_prefix: str, pattern='*', exclude_dirs=None):
    """递归添加目录内容到打包列表

    Args:
        src_dir: 源目录
        dst_prefix: 目标前缀
        pattern: 文件匹配模式
        exclude_dirs: 要排除的目录名称列表（如 ['build', 'dist', '__pycache__']）
    """
    if not src_dir.exists():
        print(f"[警告] 目录不存在: {src_dir}")
        return

    if exclude_dirs is None:
        exclude_dirs = []

    for item in src_dir.rglob(pattern):
        if item.is_file():
            # 检查路径中是否包含排除的目录
            rel_path = item.relative_to(src_dir)
            should_exclude = any(excluded_dir in rel_path.parts for excluded_dir in exclude_dirs)
            if should_exclude:
                continue

            dst_path = f"{dst_prefix}/{rel_path.parent}"
            datas.append((str(item), dst_path))

# 1. 包含文档和配置文件（评分标准、模板等）
add_directory_contents(docs_dir / 'rubrics', 'data/rubrics', '*.json')
add_directory_contents(docs_dir / 'templates', 'data/templates', '*.docx')
add_directory_contents(docs_dir / 'templates', 'data/templates', '*.md')

# 2. 包含templates目录
add_directory_contents(templates_dir, 'data/templates', '*.md')

# 3. 包含核心tools文件
tool_scripts = [
    'submission_utils.py',
    'enhanced_quality_assessment.py',
    'plagiarism_detection_enhanced.py',
    'generate_grading_excel.py',
]
for script in tool_scripts:
    file_path = tools_dir / script
    if file_path.exists():
        datas.append((str(file_path), 'tools'))

# 4. 包含security模块（安全工具集）
add_directory_contents(security_dir, 'tools/security', '*.py')

# 4.5 包含plagiarism模块（查重工具集）
plagiarism_dir = tools_dir / 'plagiarism'
if plagiarism_dir.exists():
    add_directory_contents(plagiarism_dir, 'tools/plagiarism', '*.py')

# 4.6 包含tools模块的__init__.py（重要：使tools成为有效的Python包）
tools_init = tools_dir / '__init__.py'
if tools_init.exists():
    datas.append((str(tools_init), 'tools'))

# 5. 包含配置文件
config_files = ['security_config.json']
for cfg in config_files:
    cfg_path = tools_dir / cfg
    if cfg_path.exists():
        datas.append((str(cfg_path), 'config'))

# 6. 包含app目录本身（Python模块）
add_directory_contents(spec_dir / "app", 'app', '*.py')

# 7. 包含测试数据（完整打包）
test_data_dir = spec_dir / "test_data"
if test_data_dir.exists():
    # 打包所有测试数据子目录
    for category in ['students', 'submissions', 'templates', 'rubrics', 'results']:
        category_dir = test_data_dir / category
        if category_dir.exists():
            add_directory_contents(category_dir, f'data/{category}', '*')
    # 也打包 README
    readme_file = test_data_dir / 'README.txt'
    if readme_file.exists():
        datas.append((str(readme_file), 'data/'))
    # 打包 teaching_demo 目录（用于多班级功能）
    teaching_demo_dir = test_data_dir / 'teaching_demo'
    if teaching_demo_dir.exists():
        add_directory_contents(teaching_demo_dir, 'data/teaching_demo', '*')

# 8. 包含真实教学数据（2026-春季）作为备用
teaching_data_dir = project_root / "docs" / "teaching" / "2026-春季"
if teaching_data_dir.exists():
    # 打包所有班级数据
    for class_dir in teaching_data_dir.iterdir():
        if class_dir.is_dir() and class_dir.name.endswith('班'):
            # 打包班级的所有数据
            add_directory_contents(class_dir, f'data/teaching_demo/2026-春季/{class_dir.name}', '*')

print(f"[打包配置] 收集了 {len(datas)} 个数据文件")

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(spec_dir), str(project_root)],
    binaries=binaries,
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
        # 机器学习
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
        # 语义检测（可选）
        'sentence_transformers',
        'transformers',
        'torch',
        # HTML 处理
        'markdown',
        'markdown.extensions',
        # XML 解析
        'defusedxml',
        'defusedxml.ElementTree',
        'xml.etree.ElementTree',
        # 查重模块
        'tools',  # 添加 tools 包本身
        'tools.plagiarism',
        'tools.plagiarism.core',
        'tools.plagiarism.core.multi_class_detector',
        'tools.plagiarism.core.detector',
        'tools.plagiarism.core.algorithms',
        'tools.plagiarism.core.algorithms_enhanced',
        'tools.plagiarism.report',
        'tools.plagiarism.report.multi_class_report',
        'tools.plagiarism.utils',
        'tools.plagiarism.utils.config',
        'tools.plagiarism.utils.template',
        'tools.plagiarism.utils.student_progress_tracker',
        'tools.plagiarism.utils.team_collaboration_analyzer',
        'tools.plagiarism.feedback',
        'tools.plagiarism.feedback.unified_feedback',
        'tools.plagiarism.feedback.enhanced_feedback',
        'tools.plagiarism.feedback.feedback',
        'tools.plagiarism.feedback.smart_feedback',
        'tools.plagiarism.grading',
        'tools.plagiarism.grading.grading',
        'tools.plagiarism.grading.enhanced_grading',
        'tools.plagiarism.grading.enhanced_grading_system',
        'tools.plagiarism.grading.grading_validator',
        'tools.plagiarism.grading.parallel_grading',
        'tools.plagiarism.grading.semantic_answer_grader',
        'tools.plagiarism.quality',
        'tools.plagiarism.quality.technical_checks',
        'tools.plagiarism.quality.quality',
        'tools.plagiarism.quality.adaptive_threshold',
        'tools.plagiarism.semantic',
        'tools.plagiarism.semantic.detector',
        'tools.plagiarism.semantic.enhanced',
        'tools.plagiarism.nlp',
        'tools.plagiarism.nlp.code_analyzer_nlp',
        'tools.plagiarism.nlp.enhanced_grading',
        'tools.plagiarism.nlp.enhanced_matcher',
        'tools.plagiarism.nlp.nlp_integration',
        'tools.plagiarism.nlp.template_filter',
        'tools.plagiarism.code_analysis',
        'tools.plagiarism.code_analysis.code_analyzer',
        'tools.plagiarism.code_analysis.code_quality_analyzer',
        'tools.plagiarism.code_analysis.simplified_code_checker',
        'tools.plagiarism.code_obfuscation',
        'tools.plagiarism.code_obfuscation.detector',
        'tools.plagiarism.image_similarity',
        'tools.plagiarism.image_similarity.hash',
        'tools.plagiarism.image_similarity.detector',
        'tools.plagiarism.image_quality',
        'tools.plagiarism.image_quality.metrics',
        'tools.plagiarism.image_quality.content_analyzer',
        'tools.plagiarism.image_quality.validators',
        'tools.plagiarism.image_quality.detector',
        'tools.plagiarism.ai_detection',
        'tools.plagiarism.ai_detection.detector',
        'tools.plagiarism.ai_detection.enhanced_detector',
        'tools.plagiarism.image',
        'tools.plagiarism.image.image_counter',
        'tools.plagiarism.image.image_quality_checker',
        # 提交工具模块
        'tools.submission_utils',
        'tools.security.zip_validator',
        'tools.security.xml_parser',
        'tools.security.path_validator',
        'tools.security.anonymizer',
        'tools.security',
    ],
    hookspath=[spec_dir],  # 查找当前目录下的 hook 文件
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
        'tkinter',
        'django',
        'flask',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if ONEDIR_MODE:
    # === 目录模式（推荐） ===
    # 启动快，文件便于管理
    exe = EXE(
        pyz,
        a.scripts,
        [],
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
        icon=str(icon_file) if icon_file.exists() else None,
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
else:
    # === 单文件模式 ===
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
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=str(icon_file) if icon_file.exists() else None,
        version=str(version_file) if version_file.exists() else None,
    )

# === 测试工具（可选） ===
if INCLUDE_TEST_TOOL:
    # 创建测试工具的 Analysis
    test_a = Analysis(
        ['test_import.py'],
        pathex=[str(spec_dir), str(project_root)],
        binaries=[],
        datas=[],
        hiddenimports=[
            'PyQt6',
            'openpyxl', 'docx', 'jieba', 'sklearn', 'numpy',
            'tools.plagiarism.core.multi_class_detector',
            'tools.submission_utils',
            'tools.security',
        ],
        hookspath=[spec_dir],
        excludes=[
            'PyQt6.QtWebEngineWidgets',
            'matplotlib', 'scipy', 'IPython', 'pytest', 'pandas',
        ],
    )

    test_pyz = PYZ(test_a.pure, test_a.zipped_data)

    # 测试工具使用控制台模式，方便查看输出
    test_exe = EXE(
        test_pyz,
        test_a.scripts,
        [],
        name='STM32教学管理系统_测试工具',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True,  # 控制台模式
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
