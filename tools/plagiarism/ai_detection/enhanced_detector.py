# -*- coding: utf-8 -*-
"""
增强版AI生成内容检测器
Enhanced AI Generated Content Detector

基于多种统计特征和模式检测AI生成的内容
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


class EnhancedTextAnalyzer:
    """增强文本分析器"""

    # AI生成内容的典型特征
    AI_PATTERNS = [
        r'首先|其次|最后|总之|综上所述',  # 过度结构化
        r'值得注意的是|需要指出的是',     # AI常用过渡词
        r'一方面|另一方面',              # 对比结构
        r'不仅.*而且',                  # 递进结构
        r'虽然.*但是',                  # 转折结构
    ]

    # 句式变化模式
    SENTENCE_PATTERNS = [
        r'^然而|^因此|^所以|^此外',     # 开头词
        r'，\s*(?:从而|进而|因此)',      # 连接词
    ]

    @staticmethod
    def calculate_perplexity(text: str) -> float:
        """
        计算困惑度（增强版）

        困惑度衡量文本的可预测性
        AI生成的内容通常困惑度较低（更可预测）

        Args:
            text: 输入文本

        Returns:
            困惑度值
        """
        words = EnhancedTextAnalyzer._tokenize(text)

        if len(words) < 10:
            return 0.0

        # 计算词频
        word_freq = Counter(words)
        total_words = len(words)

        # 计算熵（Entropy）
        entropy = 0.0
        for word, count in word_freq.items():
            prob = count / total_words
            entropy -= prob * math.log2(prob + 1e-10)

        # 归一化困惑度（基于熵）
        max_entropy = math.log2(len(word_freq) + 1)
        perplexity = 2 ** entropy if max_entropy > 0 else 1.0

        # 归一化到 0-10 范围
        return min(perplexity / 10, 10.0)

    @staticmethod
    def calculate_burstiness(text: str) -> float:
        """
        计算突发性（增强版）

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

        # 计算多个维度的突发性
        metrics = []

        # 1. 句子长度变化
        lengths = [len(EnhancedTextAnalyzer._tokenize(s)) for s in sentences]
        if lengths:
            avg_length = sum(lengths) / len(lengths)
            variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
            std_dev = math.sqrt(variance)
            cv = (std_dev / avg_length) if avg_length > 0 else 0
            metrics.append(min(cv / 2.0, 1.0))  # 归一化

        # 2. 标点符号多样性
        punctuation_patterns = []
        for s in sentences:
            punct_count = len(re.findall(r'[，。！？；：、]', s))
            punctuation_patterns.append(punct_count)

        if punctuation_patterns:
            punct_cv = (max(punctuation_patterns) - min(punctuation_patterns)) / max(punctuation_patterns) if max(punctuation_patterns) > 0 else 0
            metrics.append(punct_cv)

        # 3. 词汇密度变化
        densities = []
        for s in sentences:
            tokens = EnhancedTextAnalyzer._tokenize(s)
            if tokens:
                density = len(set(tokens)) / len(tokens)
                densities.append(density)

        if densities:
            density_cv = (max(densities) - min(densities))
            metrics.append(min(density_cv, 1.0))

        # 综合突发性分数
        return sum(metrics) / len(metrics) if metrics else 0.5

    @staticmethod
    def detect_ai_patterns(text: str) -> float:
        """
        检测AI生成文本的典型模式

        Args:
            text: 输入文本

        Returns:
            AI模式分数 0-1
        """
        score = 0.0
        total_patterns = len(EnhancedTextAnalyzer.AI_PATTERNS)

        for pattern in EnhancedTextAnalyzer.AI_PATTERNS:
            if re.search(pattern, text):
                score += 1.0 / total_patterns

        # 检测句式重复度
        sentences = re.split(r'[。！？\n]+', text)
        sentence_starts = [re.match(r'^(\w{1,3})', s) for s in sentences if s.strip()]
        starts = [m.group(1) if m else '' for m in sentence_starts if m]

        if len(starts) > 5:
            start_counter = Counter(starts)
            # 如果开头词重复率高，增加AI分数
            repetition = max(start_counter.values()) / len(starts)
            if repetition > 0.3:
                score += 0.2

        return min(score, 1.0)

    @staticmethod
    def calculate_vocabulary_richness(text: str) -> float:
        """
        计算词汇丰富度

        AI生成的内容通常词汇丰富度较低

        Args:
            text: 输入文本

        Returns:
            词汇丰富度 0-1
        """
        words = EnhancedTextAnalyzer._tokenize(text)

        if len(words) < 10:
            return 0.5

        unique_words = set(words)
        richness = len(unique_words) / len(words)

        # 标准化到 0-1
        return min(richness, 1.0)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """分词"""
        # 移除标点和空白
        text = re.sub(r'[^\w一-鿿]', '', text)

        # 对于中文，按字符分割
        # 对于英文，按单词分割
        tokens = []
        current_word = ''

        for char in text:
            if '一' <= char <= '鿿':  # 中文字符
                if current_word:
                    tokens.append(current_word)
                    current_word = ''
                tokens.append(char)
            elif char.isalnum():
                current_word += char
            else:
                if current_word:
                    tokens.append(current_word)
                    current_word = ''

        if current_word:
            tokens.append(current_word)

        return tokens


class EnhancedAIGeneratorDetector:
    """增强AI生成检测器"""

    def __init__(self, threshold: float = 0.7):
        """
        初始化检测器

        Args:
            threshold: AI生成判定阈值
        """
        self.threshold = threshold
        self.analyzer = EnhancedTextAnalyzer()

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
        pattern_score = self.analyzer.detect_ai_patterns(text)
        vocab_richness = self.analyzer.calculate_vocabulary_richness(text)

        # 各项指标详情
        indicators = {
            'perplexity': perplexity,
            'burstiness': burstiness,
            'pattern_score': pattern_score,
            'vocabulary_richness': vocab_richness
        }

        # 综合判断（简化版）
        # AI生成特征：低困惑度、低突发性、高模式分数、低词汇丰富度
        ai_indicators = []

        # 低困惑度 (< 5)
        if perplexity < 5:
            ai_indicators.append((5 - perplexity) / 5)

        # 低突发性 (< 0.4)
        if burstiness < 0.4:
            ai_indicators.append((0.4 - burstiness) / 0.4)

        # 高模式分数 (> 0.5)
        if pattern_score > 0.5:
            ai_indicators.append(pattern_score - 0.5)

        # 低词汇丰富度 (< 0.6)
        if vocab_richness < 0.6:
            ai_indicators.append((0.6 - vocab_richness) / 0.6)

        # 计算综合概率
        probability = sum(ai_indicators) / 4 if ai_indicators else 0.0

        # 置信度基于指标一致性
        confidence = len(ai_indicators) / 4

        # 判定是否AI生成
        is_ai_generated = probability >= self.threshold

        return AIGenerationResult(
            is_ai_generated=is_ai_generated,
            probability=probability,
            confidence=confidence,
            perplexity=perplexity,
            burstiness=burstiness,
            pattern_score=pattern_score,
            indicators=indicators
        )
