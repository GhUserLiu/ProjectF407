#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强评分系统集成模块
Enhanced Grading System Integration

v2.6.0 - 集成所有新增评分功能：
1. 抄袭自动扣分
2. 简化代码质量分析
3. 图片数量检测
4. 时间投入评估
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# 导入评分模块
from tools.plagiarism.grading import (
    GradingResult,
    RubricGrader,
    RubricLoader,
    batch_grade,
    apply_plagiarism_penalty,
    PlagiarismThresholds,
    _calculate_grade_from_percentage
)

# 导入新增模块
from tools.plagiarism.simplified_code_checker import (
    SimplifiedCodeChecker,
    CodeCheckResult
)
from tools.plagiarism.image_counter import (
    ImageCounter,
    ImageCountResult,
    check_image_count
)


@dataclass
class EnhancedGradingConfig:
    """增强评分配置"""
    # 功能开关
    enable_plagiarism_check: bool = True
    enable_code_analysis: bool = True
    enable_image_check: bool = True
    enable_time_evaluation: bool = False

    # 抄袭检测配置
    plagiarism_thresholds: PlagiarismThresholds = field(default_factory=PlagiarismThresholds)

    # 代码分析配置
    code_check_config: Dict = field(default_factory=dict)

    # 图片检测配置
    image_min_count: int = 3
    image_max_score: int = 5

    # 时间评估配置
    deadline: Optional[datetime] = None
    early_bonus_hours: int = 6


@dataclass
class EnhancedGradingResult:
    """增强评分结果"""
    # 基础评分
    base_result: GradingResult

    # 代码检查结果
    code_check: Optional[CodeCheckResult] = None

    # 图片检测结果
    image_check: Optional[ImageCountResult] = None

    # 时间评估
    time_bonus: float = 0.0

    # 最终得分
    final_score: float = 0.0
    final_grade: str = ""

    # 所有问题汇总
    all_issues: List[str] = field(default_factory=list)

    # 所有优势汇总
    all_strengths: List[str] = field(default_factory=list)


class EnhancedGradingSystem:
    """增强评分系统"""

    def __init__(
        self,
        rubric_path: Path = None,
        config: EnhancedGradingConfig = None
    ):
        """
        初始化系统

        Args:
            rubric_path: 评分标准文件路径
            config: 增强评分配置
        """
        # 加载评分标准
        if rubric_path and rubric_path.exists():
            self.rubric = RubricLoader.load(rubric_path)
        else:
            self.rubric = RubricLoader.get_default_rubric()

        # 配置
        self.config = config or EnhancedGradingConfig()

        # 初始化基础评分器
        self.base_grader = RubricGrader(self.rubric, enable_nlp=True)

        # 初始化子模块
        self.code_checker = SimplifiedCodeChecker() if self.config.enable_code_analysis else None
        self.image_counter = ImageCounter() if self.config.enable_image_check else None

    def grade_student(
        self,
        student_id: str,
        name: str,
        text: str,
        docx_path: Path = None,
        is_leader: bool = False,
        experience_info: Dict = None,
        submit_time: datetime = None,
        similarity_info: Dict = None
    ) -> EnhancedGradingResult:
        """
        评估单个学生

        Args:
            student_id: 学号
            name: 姓名
            text: 报告文本
            docx_path: Word文档路径
            is_leader: 是否是组长
            experience_info: 心得体会信息
            submit_time: 提交时间
            similarity_info: 抄袭相似度信息（如果有）

        Returns:
            增强评分结果
        """
        # 1. 基础评分
        base_result = self.base_grader.grade(
            student_id=student_id,
            name=name,
            text=text,
            is_leader=is_leader,
            experience_info=experience_info
        )

        # 2. 代码质量检查
        code_check_result = None
        if self.config.enable_code_analysis and self.code_checker:
            self.code_checker.extract_code(text)
            code_check_result = self.code_checker.run_full_check(
                self.config.code_check_config
            )

            # 将代码检查分数合并到基础评分中
            if code_check_result:
                # 假设代码质量占30分
                code_score = code_check_result.total_score
                current_code_score = base_result.category_scores.get('code_quality')
                if current_code_score:
                    adjustment = code_score - current_code_score.points_earned
                    base_result.category_scores['code_quality'].points_earned = code_score
                    base_result.category_scores['code_quality'].percentage = (
                        code_score / current_code_score.points_possible * 100
                    )
                    base_result.total_score += adjustment
                    base_result.percentage = (
                        base_result.total_score / base_result.total_possible * 100
                    )

        # 3. 图片检测
        image_check_result = None
        if self.config.enable_image_check and self.image_counter:
            image_check_result = self.image_counter.grade(
                text=text,
                docx_path=docx_path,
                min_images=self.config.image_min_count,
                max_score=self.config.image_max_score
            )

            # 添加图片得分
            if image_check_result and not image_check_result.passed:
                base_result.weaknesses.append(
                    f"图片数量不足: {image_check_result.image_count}张 "
                    f"(需要至少{self.config.image_min_count}张)"
                )

        # 4. 时间评估
        time_bonus = 0.0
        if self.config.enable_time_evaluation and submit_time and self.config.deadline:
            time_diff = self.config.deadline - submit_time

            if time_diff > timedelta(hours=self.config.early_bonus_hours):
                time_bonus = 5.0  # 提前完成加5分
            elif time_diff > timedelta(0):
                time_bonus = 1.0  # 按时完成加1分

            if time_bonus > 0:
                base_result.total_score += time_bonus
                base_result.percentage = (
                    base_result.total_score / base_result.total_possible * 100
                )
                base_result.strengths.append(f"提前完成，加{time_bonus:.0f}分")

        # 5. 抄袭扣分
        if self.config.enable_plagiarism_check and similarity_info:
            apply_plagiarism_penalty(
                base_result,
                similarity_info,
                self.config.plagiarism_thresholds
            )

        # 6. 重新计算等级
        grading_scale = self.rubric.get('grading_scale', {})
        base_result.grade = _calculate_grade_from_percentage(
            base_result.percentage,
            grading_scale
        )

        # 7. 汇总问题和优势
        all_issues = list(base_result.weaknesses)
        all_strengths = list(base_result.strengths)

        if code_check_result:
            for issue in code_check_result.issues:
                all_issues.append(f"[代码] {issue.message}")

        if image_check_result and not image_check_result.passed:
            all_issues.append(f"[图片] {image_check_result.summary}")

        return EnhancedGradingResult(
            base_result=base_result,
            code_check=code_check_result,
            image_check=image_check_result,
            time_bonus=time_bonus,
            final_score=base_result.total_score,
            final_grade=base_result.grade,
            all_issues=all_issues,
            all_strengths=all_strengths
        )

    def batch_grade(
        self,
        submissions: Dict[str, Dict],
        similarity_results: Dict = None,
        group_info: Dict[str, str] = None
    ) -> List[EnhancedGradingResult]:
        """
        批量评分

        Args:
            submissions: 提交内容 {学号: {name, text, docx_path, is_leader, experience, submit_time}}
            similarity_results: 抄袭检测结果
            group_info: 小组信息

        Returns:
            增强评分结果列表
        """
        results = []

        for student_id, submission in submissions.items():
            # 准备相似度信息
            similarity_info = None
            if similarity_results and student_id in similarity_results:
                sim_results = similarity_results[student_id]
                if sim_results:
                    # 找到最高相似度
                    max_sim = max((r.overall_similarity for r in sim_results), default=0)
                    similar_to = max(
                        sim_results,
                        key=lambda r: r.overall_similarity
                    ).similar_to if sim_results else ""
                    is_cross_group = any(r.is_cross_group for r in sim_results)

                    if max_sim >= 70:
                        similarity_info = {
                            'max_similarity': max_sim,
                            'similar_to': similar_to,
                            'is_cross_group': is_cross_group,
                            'shared_count': 0
                        }

            # 执行评分
            result = self.grade_student(
                student_id=student_id,
                name=submission.get('name', ''),
                text=submission.get('text', ''),
                docx_path=submission.get('docx_path'),
                is_leader=submission.get('is_leader', False),
                experience_info=submission.get('experience'),
                submit_time=submission.get('submit_time'),
                similarity_info=similarity_info
            )

            results.append(result)

        return results


def create_enhanced_grading_system(
    rubric_path: Path = None,
    config: EnhancedGradingConfig = None
) -> EnhancedGradingSystem:
    """
    创建增强评分系统

    Args:
        rubric_path: 评分标准路径
        config: 配置

    Returns:
        增强评分系统实例
    """
    return EnhancedGradingSystem(rubric_path, config)


# 便捷函数：使用增强版rubric进行评分
def enhanced_batch_grade(
    submissions: Dict[str, Dict],
    experiment_type: str = '档位实验',
    enable_plagiarism_check: bool = True,
    enable_code_analysis: bool = True,
    enable_image_check: bool = True
) -> List[EnhancedGradingResult]:
    """
    使用增强版评分系统批量评分

    Args:
        submissions: 提交内容
        experiment_type: 实验类型
        enable_plagiarism_check: 是否启用抄袭检测
        enable_code_analysis: 是否启用代码分析
        enable_image_check: 是否启用图片检测

    Returns:
        评分结果列表
    """
    # 创建配置
    config = EnhancedGradingConfig(
        enable_plagiarism_check=enable_plagiarism_check,
        enable_code_analysis=enable_code_analysis,
        enable_image_check=enable_image_check
    )

    # 查找rubric文件
    rubric_path = Path('docs/teaching/common/rubrics/rubric_enhanced.json')
    if not rubric_path.exists():
        rubric_path = Path('docs/teaching/common/rubrics/rubric.json')

    # 创建系统
    system = EnhancedGradingSystem(rubric_path, config)

    # 执行评分
    return system.batch_grade(submissions)
