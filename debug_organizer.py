#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""调试提交整理器"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.tools.auto_grading.submission_organizer import SubmissionOrganizer

# 设置调试参数
class_zip = Path("汽服2301B班-_实验报告（第七次实验 汽车档位模拟器设计）(附件) (1).zip")
class_name = "汽服2301B班"
experiment_id = "07-car-gear"

print(f"=== 调试提交整理器 ===")
print(f"班级ZIP: {class_zip}")
print(f"班级名称: {class_name}")
print(f"实验ID: {experiment_id}")
print()

# 创建整理器
organizer = SubmissionOrganizer(Path("data"))

# 执行整理
result = organizer.process_class_submission(class_zip, class_name, experiment_id)

print(f"=== 整理结果 ===")
print(f"总学生数: {result.total_students}")
print(f"成功: {result.successful}")
print(f"失败: {result.failed}")
print(f"错误: {result.errors}")
print(f"详情: {len(result.details)} 条")

if result.details:
    print("\n=== 处理详情 ===")
    for detail in result.details:
        print(f"  {detail}")
