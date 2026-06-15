#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
语义相似度答案评分器
Semantic Answer Grader for Chinese Q&A

使用 sentence-transformers 评估学生答案与参考答案的语义相似度
特别优化用于中文教育场景
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from threading import Lock


@dataclass
class SemanticGrade:
    """语义评分结果"""
    similarity: float  # 相似度 0-100
    score: float  # 得分
    max_score: float
    passed: bool
    confidence: float  # 评分置信度 0-1
    feedback: str
    needs_review: bool  # 是否需要人工复核


class SemanticAnswerGrader:
    """语义答案评分器"""

    # 默认模型配置
    DEFAULT_MODEL = 'paraphrase-multilingual-MiniLM-L12-v2'
    MODEL_CACHE_DIR = None

    _model_instance = None
    _model_lock = Lock()

    def __init__(
        self,
        model_name: str = None,
        cache_dir: Path = None,
        auto_download: bool = True
    ):
        """
        初始化评分器

        Args:
            model_name: 模型名称（默认使用多语言轻量模型）
            cache_dir: 模型缓存目录
            auto_download: 是否自动下载模型
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self.auto_download = auto_download
        self.model = None

    @classmethod
    def _get_default_cache_dir(cls) -> Path:
        """获取默认模型缓存目录"""
        project_root = Path(__file__).parents[3]
        cache_dir = project_root / 'models' / 'sentence_transformers'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def load_model(self) -> bool:
        """
        加载语义模型（懒加载，单例模式）

        Returns:
            是否加载成功
        """
        with self._model_lock:
            if self._model_instance is not None:
                self.model = self._model_instance
                return True

            try:
                from sentence_transformers import SentenceTransformer

                print(f"[语义评分] 正在加载模型: {self.model_name}")
                print(f"[语义评分] 模型缓存目录: {self.cache_dir}")

                # 设置环境变量指向缓存目录
                os.environ['TRANSFORMERS_CACHE'] = str(self.cache_dir)
                os.environ['HF_HOME'] = str(self.cache_dir)

                self.model = SentenceTransformer(
                    self.model_name,
                    cache_folder=str(self.cache_dir)
                )

                self._model_instance = self.model
                print(f"[语义评分] 模型加载成功")
                return True

            except Exception as e:
                print(f"[语义评分] 模型加载失败: {e}")
                print(f"[语义评分] 将回退到关键词匹配")
                return False

    def grade_answer(
        self,
        student_answer: str,
        reference_answer: str,
        max_score: float = 5.0,
        threshold: float = 0.6
    ) -> SemanticGrade:
        """
        评估答案语义相似度

        Args:
            student_answer: 学生答案
            reference_answer: 参考答案
            max_score: 满分
            threshold: 及格阈值（相似度）

        Returns:
            评分结果
        """
        # 确保模型已加载
        if self.model is None:
            if not self.load_model():
                # 模型加载失败，回退到关键词匹配
                return self._fallback_grade(
                    student_answer, reference_answer, max_score
                )

        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity

            # 编码文本
            embeddings = self.model.encode(
                [student_answer, reference_answer],
                convert_to_numpy=True
            )

            # 计算余弦相似度
            similarity = cosine_similarity(
                [embeddings[0]],
                [embeddings[1]]
            )[0][0]

            # 转换为 0-100 分数
            similarity_percent = similarity * 100

            # 计算得分
            if similarity_percent >= 90:
                score = max_score
                confidence = 0.95
            elif similarity_percent >= 75:
                score = max_score * 0.8
                confidence = 0.85
            elif similarity_percent >= 60:
                score = max_score * 0.6
                confidence = 0.75
            elif similarity_percent >= 40:
                score = max_score * 0.4
                confidence = 0.65
            else:
                score = max_score * 0.2
                confidence = 0.55

            passed = similarity_percent >= (threshold * 100)

            # 生成反馈
            if similarity_percent >= 90:
                feedback = "答案与参考答案高度一致"
            elif similarity_percent >= 75:
                feedback = "答案基本正确，有少量差异"
            elif similarity_percent >= 60:
                feedback = "答案部分正确，建议改进"
            elif similarity_percent >= 40:
                feedback = "答案与参考答案相似度较低，可能存在错误"
            else:
                feedback = "答案与参考答案差异较大，建议重新思考"

            # 低置信度时标记需要复核
            needs_review = confidence < 0.7 or similarity_percent < 50

            return SemanticGrade(
                similarity=round(similarity_percent, 1),
                score=round(score, 1),
                max_score=max_score,
                passed=passed,
                confidence=round(confidence, 2),
                feedback=feedback,
                needs_review=needs_review
            )

        except Exception as e:
            print(f"[语义评分] 评分失败: {e}")
            return self._fallback_grade(
                student_answer, reference_answer, max_score
            )

    def _fallback_grade(
        self,
        student_answer: str,
        reference_answer: str,
        max_score: float
    ) -> SemanticGrade:
        """
        回退到关键词匹配评分

        Args:
            student_answer: 学生答案
            reference_answer: 参考答案
            max_score: 满分

        Returns:
            评分结果
        """
        # 简单关键词匹配
        student_lower = student_answer.lower()
        reference_lower = reference_answer.lower()

        # 提取参考答案中的关键词（长度>2的词）
        import re
        keywords = re.findall(r'[一-龥]{2,}', reference_lower)

        matched = sum(1 for kw in keywords if kw in student_lower)
        match_ratio = matched / len(keywords) if keywords else 0

        similarity = match_ratio * 100
        score = max_score * match_ratio
        passed = match_ratio >= 0.5

        return SemanticGrade(
            similarity=round(similarity, 1),
            score=round(score, 1),
            max_score=max_score,
            passed=passed,
            confidence=0.6,  # 关键词匹配置信度较低
            feedback="使用关键词匹配（模型未加载）",
            needs_review=True  # 关键词匹配结果需要复核
        )

    def batch_grade(
        self,
        answers: Dict[str, Tuple[str, str]],
        max_score: float = 5.0,
        threshold: float = 0.6
    ) -> Dict[str, SemanticGrade]:
        """
        批量评估答案

        Args:
            answers: {问题ID: (学生答案, 参考答案)}
            max_score: 满分
            threshold: 及格阈值

        Returns:
            {问题ID: 评分结果}
        """
        results = {}

        for question_id, (student_answer, reference_answer) in answers.items():
            results[question_id] = self.grade_answer(
                student_answer, reference_answer, max_score, threshold
            )

        return results


def load_reference_answers(
    rubric_path: Path = None
) -> Dict[str, str]:
    """
    从 rubric 加载参考答案

    Args:
        rubric_path: rubric 文件路径

    Returns:
        {问题ID: 参考答案}
    """
    if rubric_path is None:
        rubric_path = Path('docs/teaching/common/rubrics/rubric.json')

    if not rubric_path.exists():
        rubric_path = Path('docs/teaching/common/rubrics/rubric_enhanced.json')

    with open(rubric_path, 'r', encoding='utf-8') as f:
        rubric = json.load(f)

    reference_answers = {}

    # 从 reference_answers 节点提取
    if 'reference_answers' in rubric:
        ref = rubric['reference_answers']

        # 思考题
        if 'thinking_questions' in ref:
            for q_id, answer in ref['thinking_questions'].items():
                reference_answers[f'thinking_{q_id}'] = answer

        # 其他参考答案
        for key, value in ref.items():
            if key != 'thinking_questions' and isinstance(value, str):
                reference_answers[key] = value

    return reference_answers


def extract_student_answers(
    report_text: str,
    question_patterns: List[str] = None
) -> Dict[str, str]:
    """
    从报告中提取学生答案

    Args:
        report_text: 报告文本
        question_patterns: 问题识别模式

    Returns:
        {问题ID: 答案}
    """
    if question_patterns is None:
        question_patterns = [
            r'思考题\s*[Qq]?\s*(\d+)[：:.\s、](.*?)(?=思考题|$|思考题|问题)',
            r'问题\s*(\d+)[：:.\s、](.*?)(?=问题|$)',
            r'[Qq]\s*(\d+)[：:.\s、](.*?)(?=[$Qq]|$)'
        ]

    answers = {}

    for pattern in question_patterns:
        import re
        matches = re.findall(pattern, report_text, re.DOTALL)
        for q_id, answer in matches:
            if answer.strip():
                answers[f'question_{q_id}'] = answer.strip()

    return answers


def grade_thinking_questions(
    report_text: str,
    rubric_path: Path = None,
    grader: SemanticAnswerGrader = None
) -> List[SemanticGrade]:
    """
    评分思考题

    Args:
        report_text: 报告文本
        rubric_path: rubric 路径
        grader: 评分器实例（可选）

    Returns:
        评分结果列表
    """
    if grader is None:
        grader = SemanticAnswerGrader()

    # 加载参考答案
    reference_answers = load_reference_answers(rubric_path)

    # 提取学生答案
    student_answers = extract_student_answers(report_text)

    # 评分
    results = []
    for q_id, student_answer in student_answers.items():
        # 查找对应的参考答案
        ref_key = q_id.replace('question_', 'thinking_')
        if ref_key in reference_answers:
            result = grader.grade_answer(
                student_answer,
                reference_answers[ref_key],
                max_score=5.0
            )
            result.feedback = f"问题{q_id.split('_')[-1]}: {result.feedback}"
            results.append(result)

    return results


# 便捷函数
def quick_semantic_grade(
    student_answer: str,
    reference_answer: str,
    max_score: float = 5.0
) -> SemanticGrade:
    """
    快速语义评分

    Args:
        student_answer: 学生答案
        reference_answer: 参考答案
        max_score: 满分

    Returns:
        评分结果
    """
    grader = SemanticAnswerGrader()
    return grader.grade_answer(student_answer, reference_answer, max_score)


if __name__ == '__main__':
    # 测试代码
    print("语义相似度评分器测试")
    print("=" * 60)

    # 测试用例
    test_cases = [
        (
            "按键配置为下降沿触发",
            "按键配置为下降沿触发是因为按键按下时电平从高变低（有上拉），下降沿更可靠检测按键动作",
            "完整答案 vs 简短答案"
        ),
        (
            "DWT消抖不阻塞CPU",
            "DWT消抖使用硬件计数器，不阻塞CPU，精度高；软件延时消抖会阻塞CPU，影响实时性",
            "部分正确 vs 完整答案"
        ),
        (
            "中断服务程序应该短",
            "中断服务程序应尽可能短，因为高优先级中断会阻塞其他中断，长时间执行会影响系统实时性",
            "意思相近 vs 标准答案"
        ),
        (
            "LED是低电平点亮",
            "本实验LED是低电平点亮，代码中HAL_GPIO_WritePin(...,GPIO_PIN_RESET)点亮，SET熄灭",
            "基本正确 vs 详细答案"
        ),
        (
            "我不清楚",
            "实际汽车中档位传感器通常采用数字量信号（开关型）或总线信号（CAN/LIN）",
            "完全错误 vs 正确答案"
        )
    ]

    grader = SemanticAnswerGrader()

    for student_answer, reference_answer, description in test_cases:
        print(f"\n测试: {description}")
        print(f"学生答案: {student_answer}")
        print(f"参考答案: {reference_answer}")

        result = grader.grade_answer(student_answer, reference_answer)

        print(f"相似度: {result.similarity}%")
        print(f"得分: {result.score}/5.0")
        print(f"反馈: {result.feedback}")
        print(f"需要复核: {'是' if result.needs_review else '否'}")
