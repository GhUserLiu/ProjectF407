#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试脚本：检查模块导入"""

import sys
from pathlib import Path

# 设置路径 - 回退到项目根目录（包含 src 和 data 的目录）
script_dir = Path(__file__).parent
project_root = script_dir.parents[2]  # 从 gui_app 回退两级，再上到 src，然后到项目根
if not (project_root / 'data').exists():
    # 如果没有 data，再试一级
    project_root = project_root.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root / 'src'))  # 添加 src 目录到路径

print(f"[DEBUG] Python 路径: {sys.path[:3]}")
print(f"[DEBUG] 项目根目录: {project_root}")
print(f"[DEBUG] data 目录: {project_root / 'data'}")

# 测试导入
try:
    print("\n[TEST] 导入 tools.plagiarism.core.multi_class_detector...")
    from tools.plagiarism.core.multi_class_detector import (
        MultiClassDetector,
        MultiClassDetectionResult,
        create_multi_class_config
    )
    print("[SUCCESS] multi_class_detector 导入成功")

    print("\n[TEST] 导入 tools.plagiarism.report.multi_class_report...")
    from tools.plagiarism.report.multi_class_report import MultiClassReportGenerator
    print("[SUCCESS] multi_class_report 导入成功")

    print("\n[TEST] 导入 tools.submission.submission_utils...")
    from tools.submission.submission_utils import get_student_info
    print("[SUCCESS] submission_utils 导入成功")

    print("\n[TEST] 测试 create_multi_class_config 函数...")
    test_dir = project_root / "data" / "teaching"
    print(f"[DEBUG] 测试目录: {test_dir}")
    print(f"[DEBUG] 目录存在: {test_dir.exists()}")
    
    result = create_multi_class_config(
        base_dir=test_dir,
        semester="2026-春季",
        experiment="07-car-gear",
        class_pattern="*班"
    )
    print(f"[SUCCESS] create_multi_class_config 返回 {len(result)} 个班级")
    for cls in result:
        print(f"  - {cls.get('class_name')}: {cls.get('submissions_dir')}")

except Exception as e:
    import traceback
    print(f"[ERROR] 导入失败: {e}")
    print(traceback.format_exc())
