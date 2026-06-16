#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""控制台测试：模拟打包环境"""

import sys
from pathlib import Path

# 模拟打包环境
if getattr(sys, 'frozen', False):
    meipass = Path(sys._MEIPASS)
    print(f"[DEBUG] _MEIPASS = {meipass}")
    print(f"[DEBUG] _MEIPASS contents: {[p.name for p in meipass.iterdir()[:20]]}")

# 设置路径
project_root = Path(__file__).parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root / 'src'))

print(f"[DEBUG] sys.path[0] = {sys.path[0]}")

# 测试导入
try:
    print("\n[TEST 1] 导入 PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("[SUCCESS] PyQt6 导入成功")

    print("\n[TEST 2] 导入 app.core.multi_class_service...")
    sys.path.insert(0, str(Path(__file__).parent))
    from app.core.multi_class_service import MultiClassService, PLAGIARISM_AVAILABLE
    print(f"[SUCCESS] MultiClassService 导入成功")
    print(f"[INFO] PLAGIARISM_AVAILABLE = {PLAGIARISM_AVAILABLE}")

    print("\n[TEST 3] 创建 MultiClassService 实例...")
    service = MultiClassService()
    print("[SUCCESS] MultiClassService 实例创建成功")

    print("\n[TEST 4] 测试 discover_classes...")
    test_dir = project_root / "data" / "teaching"
    result = service.discover_classes(
        base_dir=test_dir,
        semester="2026-春季",
        experiment="07-car-gear",
        class_pattern="*班"
    )
    print(f"[SUCCESS] discover_classes 返回 {len(result)} 个班级")
    for cls in result:
        print(f"  - {cls.get('class_name')}")

except Exception as e:
    import traceback
    print(f"[ERROR] 测试失败: {e}")
    print(traceback.format_exc())

input("\n按回车键退出...")
