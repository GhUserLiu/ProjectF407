#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
整合评分引擎
Auto Grading Engine

整合多个评分模块：
- 编译检查（BuildChecker）
- 代码质量分析（EnhancedCodeAnalyzer）
- 报告内容评分（RubricGrader）

计算综合评分并生成详细反馈。
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from .config import AutoGradingConfig
from .build_checker import BuildChecker, BuildResult, BuildStatus
from .submission_processor import ProcessedSubmission


@dataclass
class CategoryScore:
    """评分类别得分"""
    category_id: str           # 类别ID
    category_name: str         # 类别名称
    max_points: float          # 满分
    earned_points: float       # 得分
    details: List[Dict] = field(default_factory=list)  # 得分详情


@dataclass
class GradingResult:
    """评分结果"""
    student_id: str            # 学号
    name: str                  # 姓名
    class_name: str            # 班级

    # 评分
    total_score: float = 0.0  # 总分
    max_score: float = 100.0  # 满分
    grade: str = "N/A"         # 等级（A/B/C/D/F）

    # 各类别得分
    category_scores: List[CategoryScore] = field(default_factory=list)

    # 详细信息
    compilation_result: Optional[BuildResult] = None
    code_analysis: Optional[Dict] = None
    report_analysis: Optional[Dict] = None

    # 反馈
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # 时间戳
    graded_at: datetime = field(default_factory=datetime.now)


class AutoGradingEngine:
    """自动评分引擎"""

    def __init__(
        self,
        config: Optional[AutoGradingConfig] = None,
        rubric_path: Optional[Path] = None
    ):
        """
        初始化评分引擎

        Args:
            config: 配置对象
            rubric_path: 评分标准文件路径
        """
        self.config = config or AutoGradingConfig()
        self.rubric_path = rubric_path

        # 初始化子模块
        self.build_checker = BuildChecker(self.config)

        # 延迟导入（避免循环依赖）
        try:
            from ..plagiarism.code_analysis.code_analyzer import EnhancedCodeAnalyzer
            from ..plagiarism.grading.grading import RubricGrader

            self.code_analyzer = EnhancedCodeAnalyzer
            self.rubric_grader = RubricGrader
        except ImportError as e:
            print(f"警告: 无法导入评分模块: {e}")
            self.code_analyzer = None
            self.rubric_grader = None

        # 加载评分标准
        self.rubric = None
        if rubric_path and rubric_path.exists():
            self.rubric = self._load_rubric(rubric_path)

    def _load_rubric(self, rubric_path: Path) -> Dict:
        """加载评分标准"""
        import json
        with open(rubric_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def grade_submission(self, submission: ProcessedSubmission) -> GradingResult:
        """
        评分单个提交

        Args:
            submission: 已处理的提交

        Returns:
            评分结果
        """
        result = GradingResult(
            student_id=submission.student_id,
            name=submission.name,
            class_name=submission.class_name
        )

        category_scores = []

        # 1. 编译检查（如果可用）
        compilation_score = self._grade_compilation(submission)
        if compilation_score:
            category_scores.append(compilation_score)
            # details是List[Dict]，获取第一个元素中的build_result
            if compilation_score.details:
                result.compilation_result = compilation_score.details[0].get('build_result')

        # 2. 代码质量分析（如果可用）
        code_quality_score = self._grade_code_quality(submission)
        if code_quality_score:
            category_scores.append(code_quality_score)
            # details是List[Dict]，获取第一个元素中的analysis
            if code_quality_score.details:
                result.code_analysis = code_quality_score.details[0].get('analysis')

        # 3. 报告内容评分（如果可用）
        report_score = self._grade_report(submission)
        if report_score:
            category_scores.append(report_score)
            # details是List[Dict]，获取第一个元素中的analysis
            if report_score.details:
                result.report_analysis = report_score.details[0].get('analysis')

        result.category_scores = category_scores

        # 计算总分
        total_points = sum(cs.earned_points for cs in category_scores)
        max_points = sum(cs.max_points for cs in category_scores)

        result.total_score = total_points
        result.max_score = max_points

        # 计算等级
        if self.rubric and 'grading_scale' in self.rubric:
            result.grade = self._calculate_grade(total_points, self.rubric['grading_scale'])
        else:
            result.grade = self._calculate_grade_default(total_points, max_points)

        # 生成反馈
        self._generate_feedback(result)

        return result

    def _grade_compilation(self, submission: ProcessedSubmission) -> Optional[CategoryScore]:
        """
        评分编译检查

        Returns:
            编译类别得分，如果无源代码则返回None
        """
        if not submission.source_path or not submission.project_info:
            return None

        max_points = 10  # 编译检查满分

        # 执行编译检查
        build_result = self.build_checker.check_build(
            submission.source_path,
            f"{submission.student_id}-{submission.name}"
        )

        # 计算得分
        if build_result.status == BuildStatus.SUCCESS:
            earned_points = max_points
            feedback = "编译通过"
        elif build_result.status == BuildStatus.FAILED:
            # 根据错误数量扣分
            if build_result.error_count == 0:
                earned_points = max_points * 0.5  # 警告但无错误
                feedback = f"编译通过但有{build_result.warning_count}个警告"
            else:
                earned_points = 0
                feedback = f"编译失败，{build_result.error_count}个错误"
        else:
            earned_points = 0
            feedback = f"无法编译: {build_result.error_message}"

        return CategoryScore(
            category_id="compilation",
            category_name="编译检查",
            max_points=max_points,
            earned_points=earned_points,
            details=[{
                'build_result': build_result,
                'feedback': feedback
            }]
        )

    def _grade_code_quality(self, submission: ProcessedSubmission) -> Optional[CategoryScore]:
        """
        评分代码质量

        Returns:
            代码质量得分，如果无代码则返回None
        """
        # 优先使用源代码文件
        code_to_analyze = ""

        if submission.source_path and submission.project_info:
            # 读取主程序文件
            main_files = submission.project_info.main_files
            if main_files:
                for main_file in main_files:
                    try:
                        code_to_analyze += main_file.read_text(encoding='utf-8', errors='ignore') + "\n\n"
                    except Exception:
                        pass

        # 如果没有源代码，使用报告中的代码块
        if not code_to_analyze and submission.code_blocks:
            code_to_analyze = "\n\n".join(submission.code_blocks)

        if not code_to_analyze.strip():
            return None

        max_points = 20  # 代码质量满分

        # 使用代码分析器
        if self.code_analyzer:
            try:
                analysis_result = self.code_analyzer.analyze(code_to_analyze)

                # 映射分数到0-20分
                earned_points = (analysis_result.total_score / 100) * max_points

                # 提取反馈
                strengths = analysis_result.strengths
                weaknesses = [f"[{i.severity.value}] {i.message}" for i in analysis_result.issues[:5]]

                return CategoryScore(
                    category_id="code_quality",
                    category_name="代码质量",
                    max_points=max_points,
                    earned_points=round(earned_points, 1),
                    details=[{
                        'analysis': {
                            'total_score': analysis_result.total_score,
                            'strengths': strengths,
                            'weaknesses': weaknesses,
                            'issue_count': len(analysis_result.issues)
                        },
                        'feedback': f"代码质量得分: {analysis_result.total_score}/100"
                    }]
                )
            except Exception as e:
                print(f"警告: 代码分析失败: {e}")

        return None

    def _grade_report(self, submission: ProcessedSubmission) -> Optional[CategoryScore]:
        """
        评分报告内容

        Returns:
            报告得分，如果无报告则返回None
        """
        if not submission.report_text:
            return None

        # 使用Rubric评分器
        if self.rubric_grader and self.rubric:
            try:
                # 准备评分数据
                grading_input = {
                    'text': submission.report_text,
                    'student_id': submission.student_id,
                    'name': submission.name
                }

                # 创建评分器实例
                grader = self.rubric_grader(self.rubric)

                # 执行评分
                grading_result = grader.grade(grading_input)

                # 计算总分（排除手动评分类别）
                auto_categories = [c for c in self.rubric.get('categories', [])
                                 if not c.get('manual_evaluation', False)]

                total_points = sum(
                    grading_result.get('category_scores', {}).get(c['id'], 0)
                    for c in auto_categories
                )
                max_points = sum(c['points'] for c in auto_categories)

                return CategoryScore(
                    category_id="report_quality",
                    category_name="报告质量",
                    max_points=max_points,
                    earned_points=total_points,
                    details=[{
                        'analysis': grading_result,
                        'feedback': f"报告得分: {total_points}/{max_points}"
                    }]
                )
            except Exception as e:
                print(f"警告: 报告评分失败: {e}")

        # 备用方案：简单的关键词评分
        return self._grade_report_simple(submission)

    def _grade_report_simple(self, submission: ProcessedSubmission) -> CategoryScore:
        """简单报告评分（备用方案）"""
        max_points = 70
        text = submission.report_text

        # 简单的评分逻辑
        score = 0

        # 检查字数
        word_count = len(text)
        if word_count > 1000:
            score += 20
        elif word_count > 500:
            score += 10

        # 检查关键章节
        keywords = {
            '实验目的': 10,
            '实验原理': 15,
            '硬件设计': 15,
            '软件设计': 15,
            '实验结果': 15,
            '心得体会': 10
        }

        for keyword, points in keywords.items():
            if keyword in text:
                score += points

        return CategoryScore(
            category_id="report_quality",
            category_name="报告质量",
            max_points=max_points,
            earned_points=min(score, max_points),
            details=[{
                'analysis': {'word_count': word_count},
                'feedback': f"简单评分: {score}/{max_points}"
            }]
        )

    def _calculate_grade(self, score: float, grading_scale: Dict) -> str:
        """根据评分标准计算等级"""
        for grade, info in grading_scale.items():
            if info['min'] <= score <= info['max']:
                return grade
        return 'F'

    def _calculate_grade_default(self, score: float, max_score: float) -> str:
        """默认等级计算"""
        percentage = (score / max_score) * 100 if max_score > 0 else 0

        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_feedback(self, result: GradingResult):
        """生成反馈"""
        # 编译检查反馈
        if result.compilation_result:
            if result.compilation_result.success:
                result.strengths.append("代码编译通过")
            else:
                result.weaknesses.append(f"代码编译失败: {result.compilation_result.error_message}")

        # 代码质量反馈
        if result.code_analysis:
            analysis = result.code_analysis
            if 'strengths' in analysis:
                result.strengths.extend(analysis['strengths'])
            if 'weaknesses' in analysis:
                result.weaknesses.extend(analysis['weaknesses'][:3])

        # 报告反馈
        if result.report_analysis:
            # 这里可以添加报告特定的反馈
            pass

    def batch_grade(self, submissions: List[ProcessedSubmission]) -> List[GradingResult]:
        """
        批量评分

        Args:
            submissions: 已处理提交列表

        Returns:
            评分结果列表
        """
        results = []

        for i, submission in enumerate(submissions):
            print(f"评分 ({i+1}/{len(submissions)}): {submission.student_id}-{submission.name}")

            result = self.grade_submission(submission)
            results.append(result)

            print(f"  得分: {result.total_score:.1f}/{result.max_score:.1f} ({result.grade})")

        return results

    def generate_class_report(self, results: List[GradingResult]) -> Dict:
        """
        生成班级报告

        Args:
            results: 评分结果列表

        Returns:
            班级报告
        """
        if not results:
            return {}

        total = len(results)
        scores = [r.total_score for r in results]

        # 统计等级分布
        grade_distribution = {}
        for r in results:
            grade_distribution[r.grade] = grade_distribution.get(r.grade, 0) + 1

        # 统计类别得分
        category_stats = {}
        for result in results:
            for cat_score in result.category_scores:
                cat_id = cat_score.category_id
                if cat_id not in category_stats:
                    category_stats[cat_id] = {
                        'name': cat_score.category_name,
                        'total_points': 0,
                        'max_points': 0,
                        'count': 0
                    }
                category_stats[cat_id]['total_points'] += cat_score.earned_points
                category_stats[cat_id]['max_points'] += cat_score.max_points
                category_stats[cat_id]['count'] += 1

        # 计算平均分
        for cat_id, stats in category_stats.items():
            if stats['count'] > 0:
                stats['average'] = stats['total_points'] / stats['count']
                stats['max_average'] = stats['max_points'] / stats['count']

        return {
            'total_students': total,
            'average_score': sum(scores) / total if total > 0 else 0,
            'max_score': results[0].max_score if results else 0,
            'grade_distribution': grade_distribution,
            'category_stats': category_stats,
            'individual_results': [
                {
                    'student_id': r.student_id,
                    'name': r.name,
                    'score': r.total_score,
                    'grade': r.grade
                }
                for r in results
            ]
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='整合评分引擎')
    parser.add_argument('class_name', type=str, help='班级名称')
    parser.add_argument('experiment_id', type=str, help='实验ID')
    parser.add_argument('--rubric', type=Path, help='评分标准文件路径')
    parser.add_argument('--base-dir', type=Path, default='data/teaching/2026-春季/', help='基础目录')

    args = parser.parse_args()

    # 导入其他模块
    from .submission_processor import SubmissionProcessor

    # 初始化
    processor = SubmissionProcessor(args.base_dir)
    engine = AutoGradingEngine(rubric_path=args.rubric)

    # 处理提交
    submissions = processor.process_class_submissions(args.class_name, args.experiment_id)

    print(f"找到 {len(submissions)} 个提交")

    # 评分
    results = engine.batch_grade(submissions)

    # 生成报告
    class_report = engine.generate_class_report(results)

    print()
    print("=" * 60)
    print("班级报告")
    print("=" * 60)
    print(f"平均分: {class_report['average_score']:.1f}")
    print(f"等级分布: {class_report['grade_distribution']}")


if __name__ == '__main__':
    main()
