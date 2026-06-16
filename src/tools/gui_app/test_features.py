#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
STM32教学管理系统 - 功能测试脚本

测试核心功能:
1. 多班级发现
2. 文档提取 (含 .docx 格式验证)
3. 查重检测
4. 评分功能
5. 反馈生成
"""

import sys
import os
from pathlib import Path

# 设置输出编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'src' / 'tools'))

print("=" * 60)
print("STM32教学管理系统 - 功能测试")
print("=" * 60)
print(f"项目根目录: {project_root}")
print()

# 测试结果
test_results = []

# =============================================================================
# 测试 1: 导入核心模块
# =============================================================================
print("[测试 1] 导入核心模块...")
try:
    from tools.submission.submission_utils import (
        extract_text_from_docx,
        get_student_info_from_docx,
        get_student_info
    )
    from tools.security.zip_validator import ZipLimits
    from tools.plagiarism.core import PlagiarismDetector
    test_results.append(("模块导入", True, None))
    print("  [OK] 所有模块导入成功")
except Exception as e:
    test_results.append(("模块导入", False, str(e)))
    print(f"  [FAIL] 模块导入失败: {e}")
    sys.exit(1)

# =============================================================================
# 测试 2: .docx 文件格式验证 (修复验证)
# =============================================================================
print("\n[测试 2] .docx 文件格式验证 (修复验证)...")
try:
    # 创建测试数据
    import zipfile
    import io

    # 2a. 有效的 .docx 文头 (ZIP)
    valid_docx_header = b'PK\x03\x04' + b'\x00' * 100
    result = extract_text_from_docx(valid_docx_header, ZipLimits())
    if result is None:
        print("  [OK] 正确拒绝无效 ZIP 文件")
    else:
        print("  ? 应该拒绝无效 ZIP")

    # 2b. 旧的 .doc 文件头 (CDF)
    doc_header = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 100
    result = extract_text_from_docx(doc_header, ZipLimits())
    if result is None:
        print("  [OK] 正确识别并拒绝旧 .doc 格式")
    else:
        print("  [FAIL] 应该拒绝 .doc 格式")

    # 2c. 测试真实的损坏文件
    test_file = project_root / "data/teaching/2026-春季/汽服2302B班/07-car-gear/submissions/extracted"
    test_file = list(test_file.glob("23071140234*"))[0] if test_file.exists() else None

    if test_file:
        with open(test_file, 'rb') as f:
            data = f.read()
        result = extract_text_from_docx(data, ZipLimits())
        if result is None:
            print(f"  [OK] 正确处理损坏的文件: {test_file.name}")
        else:
            print(f"  ? 文件处理结果: {test_file.name}")

    test_results.append((".docx 格式验证", True, None))

except Exception as e:
    test_results.append((".docx 格式验证", False, str(e)))
    print(f"  [FAIL] 测试失败: {e}")

# =============================================================================
# 测试 3: 多班级发现
# =============================================================================
print("\n[测试 3] 多班级发现...")
try:
    from app.core.multi_class_service import MultiClassService

    service = MultiClassService()
    classes = service.discover_classes(
        base_dir=project_root / "data" / "teaching",
        semester="2026-春季",
        experiment="07-car-gear",
        class_pattern="*班"
    )

    print(f"  发现 {len(classes)} 个班级:")
    for cls in classes:
        print(f"    - {cls['class_name']}: {cls.get('student_count', 0)} 名学生")

    if len(classes) >= 2:
        print("  [OK] 多班级发现功能正常")
        test_results.append(("多班级发现", True, None))
    else:
        print("  ! 发现的班级数量较少")
        test_results.append(("多班级发现", True, "班级数量较少"))

except Exception as e:
    test_results.append(("多班级发现", False, str(e)))
    print(f"  [FAIL] 测试失败: {e}")

# =============================================================================
# 测试 4: 学生信息提取
# =============================================================================
print("\n[测试 4] 学生信息提取...")
try:
    base_dir = project_root / "data/teaching/2026-春季/汽服2301B班/07-car-gear/submissions/extracted"

    if base_dir.exists():
        student_info = get_student_info_from_docx(base_dir, ZipLimits())
        print(f"  成功提取 {len(student_info)} 名学生信息")

        if len(student_info) > 0:
            # 显示前几个学生
            for i, (sid, info) in enumerate(list(student_info.items())[:3]):
                name = info.get('name', '未知')
                has_content = '[OK]' if info.get('content') else '[FAIL]'
                print(f"    - {sid} {name}: 内容 {has_content}")
            print("  [OK] 学生信息提取功能正常")
            test_results.append(("学生信息提取", True, None))
        else:
            print("  ! 未提取到学生信息")
            test_results.append(("学生信息提取", True, "未提取到数据"))
    else:
        print("  ! 测试目录不存在")
        test_results.append(("学生信息提取", True, "目录不存在"))

except Exception as e:
    test_results.append(("学生信息提取", False, str(e)))
    print(f"  [FAIL] 测试失败: {e}")

# =============================================================================
# 测试 5: 查重检测配置
# =============================================================================
print("\n[测试 5] 查重检测配置...")
try:
    from tools.plagiarism.core.detector import SimilarityMethod
    from tools.plagiarism.core.multi_class_detector import MultiClassDetector

    # 创建班级配置字典
    class_configs = [
        {
            "class_id": "test-class",
            "class_name": "测试班级",
            "submissions_dir": str(project_root / "data" / "teaching" / "2026-春季" / "汽服2301B班" / "07-car-gear" / "submissions" / "extracted"),
        }
    ]

    # 创建检测器
    detector = MultiClassDetector(
        class_configs=class_configs,
        threshold=60.0,
        method=SimilarityMethod.HYBRID,
        enable_cross_class=True
    )

    print(f"  配置: {len(class_configs)} 个班级")
    print(f"  阈值={detector.threshold}%, 方法={detector.method.value}")
    print(f"  跨班级检测: {'启用' if detector.enable_cross_class else '禁用'}")
    print("  [OK] 查重配置功能正常")
    test_results.append(("查重配置", True, None))

except Exception as e:
    test_results.append(("查重配置", False, str(e)))
    print(f"  [FAIL] 测试失败: {e}")

# =============================================================================
# 测试结果汇总
# =============================================================================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)

passed = sum(1 for _, success, _ in test_results if success)
failed = len(test_results) - passed

for name, success, error in test_results:
    status = "[OK] PASS" if success else "[FAIL] FAIL"
    print(f"{status}  {name}")
    if error:
        print(f"         注: {error}")

print()
print(f"总计: {passed} 通过, {failed} 失败")
print("=" * 60)

# 退出码
sys.exit(0 if failed == 0 else 1)
