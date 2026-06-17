#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""完整的批阅流程测试"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.tools.auto_grading.config import AutoGradingConfig
from src.tools.auto_grading.facade import AutoGradingFacade

# 测试参数
class_zip = Path("汽服2301B班-07-car-gear.zip")
class_name = "汽服2301B班"
experiment_id = "07-car-gear"

print("=== 完整批阅流程测试 ===")
print(f"班级ZIP: {class_zip}")
print(f"班级名称: {class_name}")
print(f"实验ID: {experiment_id}")
print()

# 创建配置
config = AutoGradingConfig()

# 创建门面
facade = AutoGradingFacade(config)

# 执行完整的批阅流程
try:
    result = facade.run_full_pipeline(
        class_zip=class_zip,
        class_name=class_name,
        experiment_id=experiment_id
    )

    print(f"\n=== 批阅结果 ===")
    print(f"班级: {result.class_name}")
    print(f"实验: {result.experiment_id}")
    print(f"总提交数: {result.total_submissions}")
    print(f"成功批阅: {result.successful_graded}")
    print(f"开始时间: {result.started_at}")
    print(f"完成时间: {result.completed_at}")

    if result.grading_results:
        print(f"\n=== 评分详情 ===")
        for grading in result.grading_results[:3]:  # 只显示前3个
            print(f"学号: {grading.student_id}")
            print(f"姓名: {grading.name}")
            print(f"总分: {grading.total_score}")
            print(f"等级: {grading.grade}")
            print(f"评分类别数: {len(grading.category_scores)}")
            for cs in grading.category_scores:
                print(f"  - {cs.category_name}: {cs.earned_points}/{cs.max_points}")
            print()

except Exception as e:
    print(f"批阅失败: {e}")
    import traceback
    traceback.print_exc()
