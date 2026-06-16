#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化批阅统一门面
Auto Grading Facade

提供统一的入口，协调所有模块：
1. 整理提交格式（SubmissionOrganizer）
2. 处理提交数据（SubmissionProcessor）
3. 执行编译检查（BuildChecker）
4. 运行评分引擎（AutoGradingEngine）
5. 生成最终报告

使用示例:
    facade = AutoGradingFacade()
    result = facade.run_full_pipeline("汽服2302B班", "07-car-gear")
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

from .config import AutoGradingConfig
from .submission_organizer import SubmissionOrganizer, OrganizationResult
from .submission_processor import SubmissionProcessor, ProcessedSubmission
from .grading_engine import AutoGradingEngine, GradingResult
from .build_checker import BuildResult, BuildStatus


def serialize_details(details):
    """序列化details中的不可序列化对象"""
    if isinstance(details, list):
        return [serialize_details(item) for item in details]
    elif isinstance(details, dict):
        return {k: serialize_details(v) for k, v in details.items()}
    elif isinstance(details, BuildResult):
        return {
            'status': details.status.value if isinstance(details.status, BuildStatus) else str(details.status),
            'project_name': details.project_name,
            'success': details.success,
            'duration': details.duration,
            'error_count': details.error_count,
            'warning_count': details.warning_count,
            'error_message': details.error_message,
            'output': details.output
        }
    else:
        return details


@dataclass
class PipelineResult:
    """批阅流水线结果"""
    class_name: str                  # 班级
    experiment_id: str                # 实验

    # 各阶段结果
    organization_result: Optional[OrganizationResult] = None
    grading_results: List[GradingResult] = field(default_factory=list)

    # 统计
    total_submissions: int = 0
    successful_graded: int = 0

    # 时间戳
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class AutoGradingFacade:
    """自动化批阅统一门面"""

    def __init__(self, config: Optional[AutoGradingConfig] = None):
        """
        初始化门面

        Args:
            config: 配置对象
        """
        self.config = config or AutoGradingConfig()

        # 初始化子模块
        self.organizer = SubmissionOrganizer(self.config.data_dir)
        self.processor = SubmissionProcessor(self.config.data_dir)
        self.engine = AutoGradingEngine(self.config)

    def run_full_pipeline(
        self,
        class_zip: Path,
        class_name: str,
        experiment_id: str,
        skip_organization: bool = False
    ) -> PipelineResult:
        """
        运行完整的批阅流水线

        Args:
            class_zip: 班级压缩包路径
            class_name: 班级名称
            experiment_id: 实验ID
            skip_organization: 跳过整理阶段（如果已经整理过）

        Returns:
            流水线结果
        """
        result = PipelineResult(
            class_name=class_name,
            experiment_id=experiment_id
        )

        print("=" * 70)
        print("自动化批阅系统")
        print("=" * 70)
        print(f"班级: {class_name}")
        print(f"实验: {experiment_id}")
        print(f"开始时间: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 阶段1: 整理提交格式
        if not skip_organization:
            print("阶段1: 整理提交格式")
            print("-" * 70)

            org_result = self.organizer.process_class_submission(
                class_zip,
                class_name,
                experiment_id
            )

            result.organization_result = org_result
            print(f"  成功: {org_result.successful}/{org_result.total_students}")
            print()

            if org_result.total_students == 0:
                print("警告: 没有找到学生提交，终止处理")
                return result
        else:
            print("阶段1: 跳过（已整理）")
            print()

        # 阶段2: 处理提交数据
        print("阶段2: 处理提交数据")
        print("-" * 70)

        submissions = self.processor.process_class_submissions(
            class_name,
            experiment_id
        )

        result.total_submissions = len(submissions)
        print(f"  处理完成: {len(submissions)} 个提交")
        print()

        if not submissions:
            print("警告: 没有找到提交数据，终止处理")
            return result

        # 阶段3: 批量评分
        print("阶段3: 批量评分")
        print("-" * 70)

        grading_results = self.engine.batch_grade(submissions)
        result.grading_results = grading_results
        result.successful_graded = len(grading_results)

        print()

        # 阶段4: 生成报告
        print("阶段4: 生成报告")
        print("-" * 70)

        result.completed_at = datetime.now()

        class_report = self.engine.generate_class_report(grading_results)
        self._save_reports(result, class_report)

        print(f"  班级报告已生成")
        print(f"  个人报告已生成")

        print()
        print("=" * 70)
        print("批阅完成！")
        print("=" * 70)
        print(f"平均分: {class_report['average_score']:.1f}")
        print(f"等级分布: {class_report['grade_distribution']}")
        print(f"完成时间: {result.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"耗时: {(result.completed_at - result.started_at).total_seconds():.1f}秒")

        return result

    def run_single_submission(
        self,
        report_path: Path,
        source_path: Optional[Path] = None
    ) -> Optional[GradingResult]:
        """
        评分单个提交

        Args:
            report_path: 报告文件路径
            source_path: 源代码目录路径（可选）

        Returns:
            评分结果
        """
        print(f"评分单个提交: {report_path.name}")

        # 处理提交
        submission = self.processor.process_single_submission(
            report_path,
            source_path
        )

        if not submission:
            print("错误: 无法处理提交")
            return None

        # 评分
        result = self.engine.grade_submission(submission)

        print(f"  得分: {result.total_score:.1f}/{result.max_score:.1f} ({result.grade})")

        return result

    def _save_reports(self, pipeline_result: PipelineResult, class_report: Dict):
        """
        保存报告

        Args:
            pipeline_result: 流水线结果
            class_report: 班级报告
        """
        output_dir = self.config.get_output_dir(
            pipeline_result.class_name,
            pipeline_result.experiment_id
        )

        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存班级报告
        report_path = output_dir / "班级报告.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(class_report, f, ensure_ascii=False, indent=2)

        # 保存个人报告
        individuals_dir = output_dir / "个人报告"
        individuals_dir.mkdir(exist_ok=True)

        for grading_result in pipeline_result.grading_results:
            filename = f"{grading_result.student_id}-{grading_result.name}-评分.json"
            individual_path = individuals_dir / filename

            # 准备个人报告数据
            individual_report = {
                'student_id': grading_result.student_id,
                'name': grading_result.name,
                'class_name': grading_result.class_name,
                'total_score': grading_result.total_score,
                'max_score': grading_result.max_score,
                'grade': grading_result.grade,
                'category_scores': [
                    {
                        'category_id': cs.category_id,
                        'category_name': cs.category_name,
                        'max_points': cs.max_points,
                        'earned_points': cs.earned_points,
                        'details': serialize_details(cs.details)
                    }
                    for cs in grading_result.category_scores
                ],
                'strengths': grading_result.strengths,
                'weaknesses': grading_result.weaknesses,
                'suggestions': grading_result.suggestions,
                'graded_at': grading_result.graded_at.isoformat()
            }

            with open(individual_path, 'w', encoding='utf-8') as f:
                json.dump(individual_report, f, ensure_ascii=False, indent=2)

        # 保存汇总报告
        summary_path = output_dir / "批阅汇总.txt"
        self._save_summary_report(pipeline_result, class_report, summary_path)

    def _save_summary_report(
        self,
        pipeline_result: PipelineResult,
        class_report: Dict,
        output_path: Path
    ):
        """保存汇总报告（文本格式）"""
        lines = [
            "=" * 70,
            "自动化批阅汇总报告",
            "=" * 70,
            f"班级: {pipeline_result.class_name}",
            f"实验: {pipeline_result.experiment_id}",
            f"批阅时间: {pipeline_result.completed_at.strftime('%Y-%m-%d %H:%M:%S') if pipeline_result.completed_at else '进行中'}",
            "",
            "统计信息",
            "-" * 70,
            f"总提交数: {pipeline_result.total_submissions}",
            f"成功批阅: {pipeline_result.successful_graded}",
            f"平均分: {class_report['average_score']:.1f}",
            f"满分: {class_report['max_score']:.1f}",
            "",
            "等级分布",
            "-" * 70,
        ]

        for grade, count in sorted(class_report['grade_distribution'].items()):
            lines.append(f"  {grade}: {count}人")

        lines.extend([
            "",
            "各类别平均分",
            "-" * 70,
        ])

        for cat_id, stats in class_report['category_stats'].items():
            lines.append(f"  {stats['name']}: {stats['average']:.1f}/{stats['max_average']:.1f}")

        lines.extend([
            "",
            "个人得分",
            "-" * 70,
        ])

        # 按得分排序
        sorted_results = sorted(
            class_report['individual_results'],
            key=lambda x: x['score'],
            reverse=True
        )

        for item in sorted_results:
            lines.append(f"  {item['student_id']}-{item['name']}: {item['score']:.1f} ({item['grade']})")

        lines.append("=" * 70)

        output_path.write_text("\n".join(lines), encoding='utf-8')


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='自动化批阅系统')
    parser.add_argument('class_zip', type=Path, help='班级压缩包路径')
    parser.add_argument('class_name', type=str, help='班级名称')
    parser.add_argument('experiment_id', type=str, help='实验ID')
    parser.add_argument('--skip-organization', action='store_true', help='跳过整理阶段')
    parser.add_argument('--base-dir', type=Path, default='data/teaching/2026-春季/', help='基础目录')

    args = parser.parse_args()

    # 创建门面
    facade = AutoGradingFacade()

    # 运行流水线
    result = facade.run_full_pipeline(
        args.class_zip,
        args.class_name,
        args.experiment_id,
        skip_organization=args.skip_organization
    )

    print()
    print(f"报告已保存到: {facade.config.get_output_dir(args.class_name, args.experiment_id)}")


if __name__ == '__main__':
    main()
