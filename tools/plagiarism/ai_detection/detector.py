# -*- coding: utf-8 -*-
"""
AI生成内容检测器
AI Generated Content Detector

基于统计特征检测AI生成的内容
"""

import re
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import Counter


@dataclass
class AIGenerationResult:
    """AI生成检测结果"""
    is_ai_generated: bool            # 是否AI生成
    probability: float               # AI生成概率 0-1
    confidence: float                # 检测置信度 0-1
    perplexity: float                # 困惑度指标
    burstiness: float                # 突发性指标
    pattern_score: float            # 模式分数
    indicators: Dict[str, float]    # 各项指标详情


class TextStatisticsAnalyzer:
    """文本统计分析器"""

    @staticmethod
    def calculate_perplexity(text: str) -> float:
        """
        计算困惑度（简化版）

        困惑度衡量文本的可预测性
        AI生成的内容通常困惑度较低（更可预测）

        Args:
            text: 输入文本

        Returns:
            困惑度值
        """
        # 分词
        words = TextStatisticsAnalyzer._tokenize(text)

        if len(words) < 10:
            return 0.0

        # 计算词频
        word_freq = Counter(words)
        total_words = len(words)

        # 计算词概率分布
        word_prob = {word: count / total_words for word, count in word_freq.items()}

        # 计算困惑度（简化版）
        # 使用词频的逆作为困惑度估计
        unique_ratio = len(word_freq) / total_words
        perplexity = 1 / (unique_ratio + 0.01)

        return min(perplexity, 10.0)  # 限制最大值

    @staticmethod
    def calculate_burstiness(text: str) -> float:
        """
        计算突发性

        突发性衡量句子长度和复杂度的变化
        AI生成的内容通常突发性较低（更均匀）

        Args:
            text: 输入文本

        Returns:
            突发性值 0-1
        """
        # 提取句子
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

        if len(sentences) < 3:
            return 0.5

        # 计算句子长度
        lengths = [len(TextStatisticsAnalyzer._tokenize(s)) for s in sentences]

        if not lengths:
            return 0.5

        # 计算长度的标准差与平均值的比值（变异系数）
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        std_dev = math.sqrt(variance)

        if avg_length == 0:
            return 0.5

        cv = std_dev / avg_length  # 变异系数

        # 归一化到0-1
        burstiness = min(cv / 2.0, 1.0)

        return burstiness

    @staticmethod
    def calculate_vocab_richness(text: str) -> float:
        """
        计算词汇丰富度

        Args:
            text: 输入文本

        Returns:
            词汇丰富度 0-1
        """
        words = TextStatisticsAnalyzer._tokenize(text)

        if len(words) < 10:
            return 0.0

        unique_words = len(set(words))
        total_words = len(words)

        return unique_words / total_words

    @staticmethod
    def calculate_sentence_complexity(text: str) -> float:
        """
        计算句子复杂度

        Args:
            text: 输入文本

        Returns:
            平均复杂度
        """
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

        if not sentences:
            return 0.0

        complexities = []

        for sent in sentences:
            # 计算从句数量（简单估计：逗号、分号数量）
            clauses = sent.count('，') + sent.count('；') + 1
            # 计算平均词长
            words = TextStatisticsAnalyzer._tokenize(sent)
            if words:
                avg_word_len = sum(len(w) for w in words) / len(words)
            else:
                avg_word_len = 0
            # 复杂度 = 从句数 * 平均词长
            complexity = clauses * (1 + avg_word_len / 10)
            complexities.append(complexity)

        return sum(complexities) / len(complexities) if complexities else 0.0

    @staticmethod
    def detect_repetitive_patterns(text: str) -> float:
        """
        检测重复模式

        AI生成的内容可能包含重复的句式

        Args:
            text: 输入文本

        Returns:
            重复模式分数 0-1
        """
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) < 2:
            return 0.0

        # 检查句子开头的重复
        starters = []
        for sent in sentences:
            # 提取前两个字
            if len(sent) >= 2:
                starters.append(sent[:2])

        # 计算开头重复率
        starter_counter = Counter(starters)
        max_repeat = max(starter_counter.values()) if starter_counter else 0

        repeat_ratio = max_repeat / len(sentences) if sentences else 0

        return repeat_ratio

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """分词"""
        # 移除标点
        text = re.sub(r'[^\w一-鿿]', ' ', text)
        # 提取词
        words = re.findall(r'[一-鿿]{2,}|[a-zA-Z]{2,}', text)
        return words


class AIGeneratedDetector:
    """AI生成内容检测器"""

    def __init__(self, threshold: float = 0.6):
        """
        初始化检测器

        Args:
            threshold: AI判定阈值
        """
        self.threshold = threshold
        self.analyzer = TextStatisticsAnalyzer()

    def detect(self, text: str) -> AIGenerationResult:
        """
        检测文本是否为AI生成

        Args:
            text: 输入文本

        Returns:
            AI生成检测结果
        """
        # 计算各项指标
        perplexity = self.analyzer.calculate_perplexity(text)
        burstiness = self.analyzer.calculate_burstiness(text)
        vocab_richness = self.analyzer.calculate_vocab_richness(text)
        complexity = self.analyzer.calculate_sentence_complexity(text)
        repetitive = self.analyzer.detect_repetitive_patterns(text)

        # 计算AI生成概率
        # 低困惑度 + 低突发性 + 低词汇丰富度 + 高重复性 = 可能AI生成
        ai_score = 0.0

        # 困惑度（越低越可能是AI）
        perplexity_score = max(0, (5 - perplexity) / 5)
        ai_score += perplexity_score * 0.25

        # 突发性（越低越可能是AI）
        burstiness_score = max(0, (1 - burstiness))
        ai_score += burstiness_score * 0.25

        # 词汇丰富度（越低越可能是AI）
        vocab_score = max(0, (0.5 - vocab_richness) / 0.5)
        ai_score += vocab_score * 0.2

        # 句子复杂度（过低或过高都可能是AI）
        complexity_score = 0
        if complexity < 1.5 or complexity > 3.5:
            complexity_score = 0.5
        ai_score += complexity_score * 0.15

        # 重复模式（越高越可能是AI）
        ai_score += repetitive * 0.15

        # 判定
        is_ai_generated = ai_score >= self.threshold

        # 计算置信度
        confidence = min(1.0, ai_score + 0.2) if is_ai_generated else max(0, 1 - ai_score)

        return AIGenerationResult(
            is_ai_generated=is_ai_generated,
            probability=ai_score,
            confidence=confidence,
            perplexity=perplexity,
            burstiness=burstiness,
            pattern_score=ai_score,
            indicators={
                'perplexity': perplexity,
                'burstiness': burstiness,
                'vocab_richness': vocab_richness,
                'complexity': complexity,
                'repetitive': repetitive,
            }
        )

    def batch_detect(self, texts: Dict[str, str]) -> Dict[str, AIGenerationResult]:
        """
        批量检测

        Args:
            texts: {学号: 文本}

        Returns:
            {学号: 检测结果}
        """
        results = {}
        for student_id, text in texts.items():
            results[student_id] = self.detect(text)
        return results

    def analyze_text_patterns(self, text: str) -> Dict:
        """
        分析文本模式特征

        Args:
            text: 输入文本

        Returns:
            模式特征字典
        """
        return {
            'avg_sentence_length': self._avg_sentence_length(text),
            'sentence_count': len(re.split(r'[。！？\n]+', text)),
            'comma_ratio': text.count('，') / max(len(text), 1),
            'question_ratio': text.count('？') / max(len(text), 1),
            'exclamation_ratio': text.count('！') / max(len(text), 1),
        }

    def _avg_sentence_length(self, text: str) -> float:
        """计算平均句子长度"""
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return 0.0

        total_chars = sum(len(s) for s in sentences)
        return total_chars / len(sentences)
