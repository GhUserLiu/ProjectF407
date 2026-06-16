# -*- coding: utf-8 -*-
"""
Test MultiClassView initialization
"""

import sys
from pathlib import Path

# Setup paths correctly
script_dir = Path(__file__).parent
# Go up to project root (stm32f407)
project_root = script_dir.parents[2]
# tools directory is under project root/src/tools
tools_src = project_root / 'src'
sys.path.insert(0, str(tools_src))

print("[DEBUG] Project root:", project_root)
print("[DEBUG] tools_src:", tools_src)
print("[DEBUG] In sys.path:", str(tools_src) in sys.path)

# Test import chain
try:
    print("\n=== Testing Import Chain ===")
    
    print("\n[1/6] Import PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("  [OK] PyQt6 imported")

    print("\n[2/6] Import tools.plagiarism.core.multi_class_detector...")
    from tools.plagiarism.core.multi_class_detector import (
        MultiClassDetector,
        MultiClassDetectionResult,
        create_multi_class_config
    )
    print("  [OK] multi_class_detector imported")

    print("\n[3/6] Import tools.plagiarism.report.multi_class_report...")
    from tools.plagiarism.report.multi_class_report import MultiClassReportGenerator
    print("  [OK] multi_class_report imported")

    print("\n[4/6] Import tools.submission.submission_utils...")
    from tools.submission.submission_utils import get_student_info
    print("  [OK] submission_utils imported")

    print("\n[5/6] Import app.core.multi_class_service...")
    sys.path.insert(0, str(script_dir))
    from app.core.multi_class_service import MultiClassService, PLAGIARISM_AVAILABLE
    print("  [OK] MultiClassService imported")
    print("  [INFO] PLAGIARISM_AVAILABLE =", PLAGIARISM_AVAILABLE)

    if not PLAGIARISM_AVAILABLE:
        print("\n[ERROR] PLAGIARISM_AVAILABLE is False!")
        print("  This is why the app shows 'plagiarism module not available'")
        sys.exit(1)

    print("\n[6/6] Create MultiClassService instance...")
    service = MultiClassService()
    print("  [OK] MultiClassService instance created")

    print("\n=== Test discover_classes ===")
    test_dir = project_root / "data" / "teaching"
    print("  [INFO] test_dir:", test_dir)
    print("  [INFO] exists:", test_dir.exists())
    
    result = service.discover_classes(
        base_dir=test_dir,
        semester="2026-春季",
        experiment="07-car-gear",
        class_pattern="*班"
    )
    print(f"[OK] discover_classes returned {len(result)} classes")
    for cls in result:
        print(f"  - {cls.get('class_name')}: {cls.get('submissions_dir')}")

    print("\n[SUCCESS] All tests passed!")

except Exception as e:
    import traceback
    print(f"\n[ERROR] Test failed:", e)
    print(traceback.format_exc())
    sys.exit(1)

input("\nPress Enter to exit...")
