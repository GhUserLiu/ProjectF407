#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于 Rubric 的评分引擎
Rubric-Based Grading Engine

根据实验评分标准（rubric.json）自动评估学生实验报告
"""

import re
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


@dataclass
class CriterionScore:
    """单个评分标准得分"""
    criterion_id: str
    description: str
    points_earned: float
    points_possible: float
    matched_keywords: List[str] = field(default_factory=list)
    feedback: str = ""


@dataclass
class CategoryScore:
    """评分类别得分"""
    category_id: str
    name: str
    points_earned: float
    points_possible: float
    percentage: float
    criteria_scores: List[CriterionScore] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)


@dataclass
class GradingResult:
    """完整评分结果"""
    student_id: str
    name: str
    total_score: float
    total_possible: float
    percentage: float
    grade: str
    category_scores: Dict[str, CategoryScore]
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    detailed_feedback: str = ""
    auto_confidence: float = 0.85  # 自动评分置信度


class RubricLoader:
    """加载评分标准"""

    @staticmethod
    def load(rubric_path: Path) -> Dict:
        """
        加载 rubric.json 文件

        Args:
            rubric_path: rubric 文件路径

        Returns:
            rubric 数据字典
        """
        if not rubric_path.exists():
            # 返回默认 rubric
            return RubricLoader.get_default_rubric()

        with open(rubric_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def get_default_rubric() -> Dict:
        """获取默认评分标准"""
        return {
            "experiment_name": "实验报告",
            "total_points": 100,
            "grading_scale": {
                "A": {"min": 90, "max": 100, "label": "优"},
                "B": {"min": 80, "max": 89, "label": "良"},
                "C": {"min": 70, "max": 79, "label": "中"},
                "D": {"min": 60, "max": 69, "label": "及格"},
                "F": {"min": 0, "max": 59, "label": "不及格"}
            },
            "categories": []
        }


class KeywordMatcher:
    """关键词匹配器"""

    def __init__(self, enable_nlp: bool = True):
        """
        初始化匹配器

        Args:
            enable_nlp: 是否启用NLP增强匹配
        """
        self.enable_nlp = enable_nlp
        self.enhanced_matcher = None

        if enable_nlp:
            try:
                from .nlp.enhanced_matcher import EnhancedKeywordMatcher
                self.enhanced_matcher = EnhancedKeywordMatcher(
                    use_fuzzy=True,
                    use_variants=True,
                    fuzzy_threshold=0.85
                )
            except ImportError:
                # NLP模块不可用，使用传统方法
                self.enable_nlp = False

    def match_keywords(self, text: str, keywords: List[str]) -> Tuple[List[str], float]:
        """
        匹配关键词

        Args:
            text: 报告文本
            keywords: 关键词列表

        Returns:
            (匹配的关键词列表, 匹配比例)
        """
        # 使用NLP增强匹配器
        if self.enable_nlp and self.enhanced_matcher:
            try:
                from .nlp.enhanced_matcher import MatchMethod
                results, ratio = self.enhanced_matcher.match_keywords(
                    text, keywords, MatchMethod.HYBRID
                )
                matched = [r.keyword for r in results if r.matched]
                return matched, ratio
            except Exception:
                # NLP匹配失败，回退到传统方法
                pass

        # 传统匹配方法（后备）
        text_lower = text.lower()
        matched = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                matched.append(keyword)

        match_ratio = len(matched) / len(keywords) if keywords else 0
        return matched, match_ratio


class SectionDetector:
    """章节检测器"""

    # 章节标题模式
    SECTION_PATTERNS = [
        r'^[一二三四五六七八九十]+[、．.]\s*(.+)$',
        r'^\d+[、．.]\s*(.+)$',
        r'^(\d+)\.\s*(.+)$',
        r'^#{1,3}\s*(.+)$',
        r'^\[([一二三四五六七八九十]+)\]\s*(.+)$',
    ]

    @staticmethod
    def detect_sections(text: str) -> Dict[str, str]:
        """
        检测报告章节

        Args:
            text: 报告文本

        Returns:
            {章节名称: 内容}
        """
        sections = {}
        lines = text.split('\n')

        current_section = "其他"
        current_content = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是章节标题
            is_section = False
            section_name = None

            for pattern in SectionDetector.SECTION_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    section_name = match.group(1) if match.groups() else line
                    is_section = True
                    break

            if is_section:
                # 保存上一个章节
                if current_content:
                    sections[current_section] = '\n'.join(current_content)

                current_section = section_name
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_content:
            sections[current_section] = '\n'.join(current_content)

        return sections

    @staticmethod
    def find_section_content(text: str, section_keywords: List[str]) -> Optional[str]:
        """
        查找包含特定关键词的章节内容

        Args:
            text: 报告文本
            section_keywords: 章节关键词列表

        Returns:
            章节内容或 None
        """
        sections = SectionDetector.detect_sections(text)

        for section_name, content in sections.items():
            for keyword in section_keywords:
                if keyword in section_name:
                    return content

        return None


class RubricGrader:
    """基于 Rubric 的评分器"""

    def __init__(self, rubric: Dict, enable_nlp: bool = True):
        """
        初始化评分器

        Args:
            rubric: 评分标准数据
            enable_nlp: 是否启用NLP增强匹配
        """
        self.rubric = rubric
        self.experiment_name = rubric.get('experiment_name', '实验')
        self.total_points = rubric.get('total_points', 100)
        self.grading_scale = rubric.get('grading_scale', {})
        self.categories = rubric.get('categories', [])
        self.enable_nlp = enable_nlp

        # 初始化关键词匹配器
        self.keyword_matcher = KeywordMatcher(enable_nlp=enable_nlp)

    def grade(self, student_id: str, name: str, text: str) -> GradingResult:
        """
        评估学生报告

        Args:
            student_id: 学号
            name: 姓名
            text: 报告文本

        Returns:
            评分结果
        """
        category_scores = {}
        total_earned = 0.0
        all_strengths = []
        all_weaknesses = []
        all_recommendations = []

        # 检测章节
        sections = SectionDetector.detect_sections(text)

        # 评估每个类别
        for category in self.categories:
            category_id = category['id']
            category_name = category['name']
            category_points = category['points']

            # 获取对应的章节内容
            source_section = category.get('source_section', '')
            section_content = self._find_section_content(sections, source_section)

            # 如果没找到对应章节，使用全文
            if not section_content:
                section_content = text

            category_score = self._grade_category(
                category, section_content, text
            )

            category_scores[category_id] = category_score
            total_earned += category_score.points_earned

            # 收集反馈
            all_strengths.extend([
                f"{category_name}: {fb}" for fb in category_score.feedback
                if "正确" in fb or "完整" in fb or "详细" in fb
            ])
            all_weaknesses.extend([
                f"{category_name}: {fb}" for fb in category_score.feedback
                if "缺少" in fb or "不足" in fb or "错误" in fb
            ])

        # 计算总分和等级
        percentage = (total_earned / self.total_points * 100) if self.total_points > 0 else 0
        grade = self._calculate_grade(percentage)

        # 生成详细反馈
        detailed_feedback = self._generate_feedback(
            category_scores, total_earned, self.total_points
        )

        return GradingResult(
            student_id=student_id,
            name=name,
            total_score=round(total_earned, 1),
            total_possible=self.total_points,
            percentage=round(percentage, 1),
            grade=grade,
            category_scores=category_scores,
            strengths=all_strengths,
            weaknesses=all_weaknesses,
            recommendations=all_recommendations,
            detailed_feedback=detailed_feedback
        )

    def _find_section_content(self, sections: Dict, source_hint: str) -> str:
        """根据提示查找章节内容"""
        # 直接匹配
        if source_hint in sections:
            return sections[source_hint]

        # 关键词匹配
        for section_name, content in sections.items():
            if any(keyword in section_name for keyword in source_hint.split()):
                return content

        return ""

    def _grade_category(
        self,
        category: Dict,
        content: str,
        full_text: str
    ) -> CategoryScore:
        """评估单个类别"""
        category_id = category['id']
        category_name = category['name']
        category_points = category['points']
        criteria = category.get('criteria', [])
        is_manual = category.get('manual_evaluation', False)

        criteria_scores = []
        category_earned = 0.0
        feedback = []

        # 手动评分类别（如实验态度）：从配置读取默认分
        if is_manual:
            default_score = category.get('default_points', 6.0)  # 从配置读取，默认6分
            category_earned = min(default_score, category_points)  # 不超过满分
            feedback.append(f"📝 教师评定（默认{default_score}分，可手动调整）")
            feedback.append(f"  - 全勤：10分")
            feedback.append(f"  - 缺勤1次：5分")
            feedback.append(f"  - 缺勤2次及以上：0分")
        else:
            # 自动评分类别：根据关键词匹配
            for criterion in criteria:
                criterion_score = self._grade_criterion(criterion, content, full_text)
                criteria_scores.append(criterion_score)
                category_earned += criterion_score.points_earned

                # 生成反馈
                if criterion_score.points_earned == criterion['points']:
                    feedback.append(f"✓ {criterion['description']}")
                elif criterion_score.points_earned > 0:
                    feedback.append(f"△ {criterion['description']} (部分)")
                else:
                    feedback.append(f"✗ {criterion['description']}")

        percentage = (category_earned / category_points * 100) if category_points > 0 else 0

        return CategoryScore(
            category_id=category_id,
            name=category_name,
            points_earned=round(category_earned, 1),
            points_possible=category_points,
            percentage=round(percentage, 1),
            criteria_scores=criteria_scores,
            feedback=feedback
        )

    def _grade_criterion(
        self,
        criterion: Dict,
        content: str,
        full_text: str
    ) -> CriterionScore:
        """评估单个标准"""
        criterion_id = criterion.get('id', '')
        description = criterion['description']
        points = criterion['points']
        keywords = criterion.get('keywords', [])

        # 在内容中查找关键词
        matched, match_ratio = self.keyword_matcher.match_keywords(content, keywords)

        # 如果在指定章节没找到，尝试在全文中查找
        if not matched and keywords:
            matched, match_ratio = self.keyword_matcher.match_keywords(full_text, keywords)

        # 根据匹配比例计算得分
        if match_ratio >= 0.8:
            earned = points
        elif match_ratio >= 0.5:
            earned = points * 0.6
        elif match_ratio >= 0.2:
            earned = points * 0.3
        else:
            earned = 0

        return CriterionScore(
            criterion_id=criterion_id,
            description=description,
            points_earned=earned,
            points_possible=points,
            matched_keywords=matched,
            feedback=f"匹配关键词: {', '.join(matched)}" if matched else "未找到关键词"
        )

    def _calculate_grade(self, percentage: float) -> str:
        """根据百分比计算等级"""
        for grade, scale in sorted(self.grading_scale.items(), key=lambda x: x[1]['min'], reverse=True):
            if scale['min'] <= percentage <= scale['max']:
                return grade
        return 'F'

    def _generate_feedback(
        self,
        category_scores: Dict[str, CategoryScore],
        total_earned: float,
        total_possible: float
    ) -> str:
        """生成详细反馈"""
        lines = [
            f"# {self.experiment_name} 评分反馈",
            "",
            f"**总分**: {total_earned}/{total_possible} ({total_earned/total_possible*100:.1f}%)",
            "",
            "## 各项得分"
        ]

        for category_id, score in category_scores.items():
            lines.append(f"\n### {score.name} ({score.points_earned}/{score.points_possible})")

            for feedback in score.feedback:
                lines.append(f"- {feedback}")

        return '\n'.join(lines)


class EnhancedRubricGrader(RubricGrader):
    """增强版 Rubric 评分器"""

    def grade(self, student_id: str, name: str, text: str) -> GradingResult:
        """增强评估"""
        result = super().grade(student_id, name, text)

        # 增强反馈
        result.recommendations = self._generate_recommendations(result, text)

        # 计算自动评分置信度
        result.auto_confidence = self._calculate_confidence(result, text)

        return result

    def _generate_recommendations(self, result: GradingResult, text: str) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于薄弱项生成建议
        for category_id, score in result.category_scores.items():
            if score.percentage < 60:
                recommendations.append(f"【{score.name}】需要加强，请补充相关内容")

        # 检查字数
        char_count = len(re.sub(r'\s', '', text))
        if char_count < 500:
            recommendations.append("报告内容偏少，建议增加详细说明")

        # 检查图表
        if not re.search(r'图|表|截图|照片', text):
            recommendations.append("建议添加图表或截图来说明实验结果")

        # 检查代码
        if not re.search(r'代码|程序|函数|HAL_|GPIO', text):
            recommendations.append("请补充关键代码说明")

        return recommendations

    def _calculate_confidence(self, result: GradingResult, text: str) -> float:
        """计算自动评分置信度"""
        confidence = 0.85  # 基础置信度

        # 根据报告质量调整
        char_count = len(re.sub(r'\s', '', text))
        if char_count < 300:
            confidence -= 0.2  # 内容太少，降低置信度
        elif char_count > 1000:
            confidence += 0.05  # 内容充分，提高置信度

        # 根据得分分布调整
        if result.percentage > 90 or result.percentage < 30:
            confidence -= 0.1  # 极端分数需要人工复核

        return max(0.5, min(confidence, 0.95))


def load_rubric_for_experiment(
    experiment_type: str,
    base_dir: Path = None
) -> Dict:
    """
    为指定实验类型加载评分标准

    Args:
        experiment_type: 实验类型（如 '07_car_gear_experiment'）
        base_dir: 基础目录

    Returns:
        rubric 数据
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent / 'docs/teaching/common/rubrics'

    rubric_file = base_dir / 'rubric.json'

    if rubric_file.exists():
        return RubricLoader.load(rubric_file)

    return RubricLoader.get_default_rubric()


def batch_grade(
    submissions: Dict[str, Dict],
    rubric: Dict,
    experiment_type: str = '档位实验',
    enable_nlp: bool = True
) -> List[GradingResult]:
    """
    批量评分

    Args:
        submissions: 提交内容 {学号: {name, text}}
        rubric: 评分标准
        experiment_type: 实验类型
        enable_nlp: 是否启用NLP增强

    Returns:
        评分结果列表
    """
    grader = EnhancedRubricGrader(rubric) if hasattr(RubricGrader, '__init__') else RubricGrader(rubric, enable_nlp=enable_nlp)
    results = []

    for student_id, submission in submissions.items():
        name = submission.get('name', '')
        text = submission.get('text', '')

        if not text:
            # 未提交
            results.append(GradingResult(
                student_id=student_id,
                name=name,
                total_score=0.0,
                total_possible=rubric.get('total_points', 100),
                percentage=0.0,
                grade='F',
                category_scores={},
                strengths=[],
                weaknesses=['未提交报告'],
                recommendations=['请尽快提交实验报告'],
                detailed_feedback="未提交报告",
                auto_confidence=1.0
            ))
            continue

        result = grader.grade(student_id, name, text)
        results.append(result)

    return results
