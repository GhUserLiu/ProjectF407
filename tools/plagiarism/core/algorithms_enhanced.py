"""
增强的相似度计算算法模块 (v2.0)
Enhanced Similarity Calculation Algorithms

改进内容：
1. 增强文本相似度检测（抵抗同义词替换）
2. 改进代码混淆检测能力
3. 优化性能
4. 减少误报
"""

import re
import math
from collections import Counter
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# 尝试导入jieba进行中文分词
try:
    import jieba
    import jieba.analyse
    HAS_JIEBA = True
except ImportError:
    HAS_JIEBA = False

# 尝试导入numpy进行性能优化
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


@dataclass
class SimilarityDetail:
    """相似度详细信息"""
    overall: float              # 整体相似度
    sequence: float             # 序列相似度
    cosine: float               # 余弦相似度
    jaccard: float              # Jaccard相似度
    keyword_match: float        # 关键词匹配度
    structure_match: float      # 结构匹配度
    confidence: float           # 结果置信度


class TextNormalizer:
    """文本规范化器 - 提高查重准确性"""

    # 常见同义词映射
    SYNONYM_MAP = {
        # 数字
        '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
        '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10',
        # 量词
        '个': '个', '只': '个', '件': '个', '台': '台', '套': '套',
        # 常见同义词
        '使用': '用', '利用': '用', '采用': '用',
        '显示': '展示', '呈现': '展示',
        '设置': '配置', '设定': '配置',
        '连接': '接', '接入': '接',
        '输出': '输出', '输出': '输出',
        '输入': '输入', '接收': '输入',
        # 电路相关
        '高电平': '高', '低电平': '低',
        '点亮': '亮', '熄灭': '灭',
        # 时间相关
        '毫秒': 'ms', '秒': 's', '微秒': 'us',
    }

    # 需要移除的常见填充词
    FILLER_WORDS = {
        '然后', '接着', '之后', '最后', '首先', '其次',
        '非常', '十分', '特别', '极其', '相当',
        '可以', '能够', '可以', '可能',
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        规范化文本

        Args:
            text: 原始文本

        Returns:
            规范化后的文本
        """
        if not text:
            return ''

        # 转小写
        text = text.lower()

        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)

        # 替换同义词
        for old, new in cls.SYNONYM_MAP.items():
            text = text.replace(old, new)

        # 移除标点符号（保留数字和字母）
        text = re.sub(r'[^\w\s]', ' ', text)

        # 移除填充词
        for filler in cls.FILLER_WORDS:
            text = text.replace(filler, ' ')

        # 再次清理空格
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    @classmethod
    def extract_keywords(cls, text: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        提取关键词（使用TF-IDF或TextRank）

        Args:
            text: 输入文本
            top_k: 返回前k个关键词

        Returns:
            关键词列表 [(词, 权重), ...]
        """
        if HAS_JIEBA:
            # 使用jieba分词和关键词提取
            keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=True)
            return keywords
        else:
            # 简单的词频统计作为后备
            words = cls._simple_tokenize(text)
            freq = Counter(words)
            return [(word, count / len(words)) for word, count in freq.most_common(top_k)]

    @classmethod
    def _simple_tokenize(cls, text: str) -> List[str]:
        """简单的分词（无jieba时）"""
        # 按字符分割（中文）和空格分割（英文）
        tokens = []
        for char in text:
            if char.isalpha():
                tokens.append(char)
            elif char.isspace():
                continue
            else:
                # 中文按单字处理
                tokens.append(char)
        return tokens


class CodeNormalizer:
    """代码规范化器 - 检测代码混淆"""

    # 代码模式（用于检测混淆）
    CODE_PATTERNS = {
        'function_def': r'(void|int|uint\d+_t|char|float|double)\s+(\w+)\s*\(',
        'variable_decl': r'(int|uint\d+_t|char|float|double)\s+(\w+)\s*[=;]',
        'hal_call': r'HAL_(GPIO|UART|TIM|ADC|SPI|I2C)_\w+\s*\(',
        'register_access': r'\w+\s*[&|]=\s*\(',
        'struct_init': r'(GPIO|TIM|UART|ADC|SPI|I2C)_\w+_TypeDef\s+',
    }

    # 变量命名混淆模式
    OBFUSCATION_PATTERNS = [
        r'[a-z]{1,2}_\d+',     # 如: a_1, x_23
        r'_[a-z]\d*',          # 如: _x1, _y2
        r'v\d+',               # 如: v1, v2, v3
        r'[x,y,z]\d*',         # 如: x, x1, x2
    ]

    @classmethod
    def normalize_code(cls, code: str) -> str:
        """
        规范化代码（去除混淆影响）

        Args:
            code: 原始代码

        Returns:
            规范化后的代码
        """
        if not code:
            return ''

        # 移除注释
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)

        # 统一空格
        code = re.sub(r'\s+', ' ', code)

        # 移除字符串字面量（避免干扰比较）
        code = re.sub(r'".*?"', "'STR'", code)
        code = re.sub(r"'.*'", "'CHAR'", code)

        # 规范化数字（用N代替）
        code = re.sub(r'\b\d+\b', 'N', code)

        return code.strip()

    @classmethod
    def extract_structure(cls, code: str) -> Dict[str, List[str]]:
        """
        提取代码结构（用于检测结构相似度）

        Args:
            code: 代码字符串

        Returns:
            结构字典 {'functions': [...], 'variables': [...], 'hal_calls': [...]}
        """
        structure = {
            'functions': [],
            'variables': [],
            'hal_calls': [],
            'control_flow': []
        }

        # 提取函数定义
        for match in re.finditer(cls.CODE_PATTERNS['function_def'], code):
            structure['functions'].append(match.group(0))

        # 提取变量声明
        for match in re.finditer(cls.CODE_PATTERNS['variable_decl'], code):
            structure['variables'].append(match.group(0))

        # 提取HAL函数调用
        for match in re.finditer(cls.CODE_PATTERNS['hal_call'], code):
            structure['hal_calls'].append(match.group(0))

        # 提取控制流语句
        control_patterns = [r'\bif\s*\(', r'\bfor\s*\(', r'\bwhile\s*\(', r'\bswitch\s*\(']
        for pattern in control_patterns:
            for match in re.finditer(pattern, code):
                structure['control_flow'].append(match.group(0))

        return structure

    @classmethod
    def detect_obfuscation(cls, code: str) -> Tuple[float, List[str]]:
        """
        检测代码混淆程度

        Args:
            code: 代码字符串

        Returns:
            (混淆分数0-100, 检测到的混淆特征列表)
        """
        if not code:
            return 0.0, []

        obfuscation_features = []
        score = 0.0

        # 检查变量命名模式
        variable_names = re.findall(r'\b([a-zA-Z_]\w*)\b', code)

        # 1. 检查短变量名比例
        short_names = [v for v in variable_names if len(v) <= 2 and v not in ['i', 'j', 'k']]
        if len(variable_names) > 0:
            short_ratio = len(short_names) / len(variable_names)
            if short_ratio > 0.5:
                score += 20
                obfuscation_features.append('高比例短变量名')

        # 2. 检查混淆模式
        for pattern in cls.OBFUSCATION_PATTERNS:
            matches = re.findall(pattern, code)
            if matches:
                score += min(len(matches) * 5, 20)
                obfuscation_features.append(f'混淆命名模式: {pattern}')

        # 3. 检查单字符变量密度
        single_char_vars = [v for v in variable_names if len(v) == 1 and v.isalpha()]
        if len(single_char_vars) > 5:
            score += 10
            obfuscation_features.append('大量单字符变量')

        return min(score, 100.0), obfuscation_features


def enhanced_sequence_similarity(text1: str, text2: str) -> SimilarityDetail:
    """
    增强的序列相似度计算

    Args:
        text1: 第一个文本
        text2: 第二个文本

    Returns:
        相似度详细信息
    """
    # 规范化文本
    norm1 = TextNormalizer.normalize(text1)
    norm2 = TextNormalizer.normalize(text2)

    if not norm1 or not norm2:
        return SimilarityDetail(0, 0, 0, 0, 0, 0, 0)

    # 1. 序列相似度
    seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100

    # 2. 余弦相似度（基于规范化文本）
    cosine_sim = cosine_similarity_normalized(norm1, norm2)

    # 3. Jaccard相似度
    jaccard_sim = jaccard_similarity_normalized(norm1, norm2)

    # 4. 关键词匹配度
    kw1 = TextNormalizer.extract_keywords(text1, top_k=10)
    kw2 = TextNormalizer.extract_keywords(text2, top_k=10)

    if kw1 and kw2:
        kw_set1 = set([w for w, _ in kw1])
        kw_set2 = set([w for w, _ in kw2])
        intersection = kw_set1 & kw_set2
        union = kw_set1 | kw_set2
        keyword_match = (len(intersection) / len(union) * 100) if union else 0
    else:
        keyword_match = 0

    # 5. 结构相似度（基于句子结构）
    struct_sim = compute_structure_similarity(norm1, norm2)

    # 计算整体相似度（加权平均）
    overall = (
        seq_sim * 0.3 +
        cosine_sim * 0.25 +
        jaccard_sim * 0.2 +
        keyword_match * 0.15 +
        struct_sim * 0.1
    )

    # 计算置信度（基于各方法的一致性）
    similarities = [seq_sim, cosine_sim, jaccard_sim, keyword_match, struct_sim]
    std_dev = math.sqrt(sum((s - overall) ** 2 for s in similarities) / len(similarities))
    confidence = max(0, 100 - std_dev * 2)  # 标准差越小，置信度越高

    return SimilarityDetail(
        overall=overall,
        sequence=seq_sim,
        cosine=cosine_sim,
        jaccard=jaccard_sim,
        keyword_match=keyword_match,
        structure_match=struct_sim,
        confidence=confidence
    )


def enhanced_code_similarity(code1: str, code2: str) -> Tuple[float, Dict]:
    """
    增强的代码相似度计算

    Args:
        code1: 第一个代码
        code2: 第二个代码

    Returns:
        (相似度分数, 详细信息)
    """
    if not code1 or not code2:
        return 0.0, {}

    # 规范化代码
    norm1 = CodeNormalizer.normalize_code(code1)
    norm2 = CodeNormalizer.normalize_code(code2)

    # 1. 规范化代码的序列相似度
    seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100

    # 2. 结构相似度
    struct1 = CodeNormalizer.extract_structure(code1)
    struct2 = CodeNormalizer.extract_structure(code2)

    struct_sim = 0.0
    if struct1 or struct2:
        # 计算各结构元素的相似度
        similarities = []
        for key in ['functions', 'variables', 'hal_calls', 'control_flow']:
            set1 = set(struct1.get(key, []))
            set2 = set(struct2.get(key, []))
            if set1 or set2:
                inter = set1 & set2
                uni = set1 | set2
                sim = (len(inter) / len(uni) * 100) if uni else 100
                similarities.append(sim)

        struct_sim = sum(similarities) / len(similarities) if similarities else 0

    # 3. 检测代码混淆
    obs1, features1 = CodeNormalizer.detect_obfuscation(code1)
    obs2, features2 = CodeNormalizer.detect_obfuscation(code2)

    # 4. 计算整体相似度（考虑混淆影响）
    # 如果存在混淆，降低序列相似度的权重
    obfuscation_penalty = (obs1 + obs2) / 200  # 0-1之间

    overall = seq_sim * (1 - obfuscation_penalty * 0.3) + struct_sim * 0.3

    return min(overall, 100.0), {
        'sequence_similarity': seq_sim,
        'structure_similarity': struct_sim,
        'obfuscation1_score': obs1,
        'obfuscation2_score': obs2,
        'obfuscation_features1': features1,
        'obfuscation_features2': features2,
        'normalized_similarity': overall
    }


def cosine_similarity_normalized(text1: str, text2: str) -> float:
    """余弦相似度（基于规范化文本）"""
    if not text1 or not text2:
        return 0.0

    words1 = _tokenize_normalized(text1)
    words2 = _tokenize_normalized(text2)

    if not words1 or not words2:
        return 0.0

    freq1 = Counter(words1)
    freq2 = Counter(words2)

    dot_product = sum(freq1[w] * freq2.get(w, 0) for w in freq1)
    norm1 = math.sqrt(sum(v ** 2 for v in freq1.values()))
    norm2 = math.sqrt(sum(v ** 2 for v in freq2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return (dot_product / (norm1 * norm2)) * 100


def jaccard_similarity_normalized(text1: str, text2: str) -> float:
    """Jaccard相似度（基于规范化文本）"""
    if not text1 or not text2:
        return 0.0

    words1 = set(_tokenize_normalized(text1))
    words2 = set(_tokenize_normalized(text2))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    if not union:
        return 0.0

    return (len(intersection) / len(union)) * 100


def compute_structure_similarity(text1: str, text2: str) -> float:
    """计算文本结构相似度"""
    # 分割成句子
    sentences1 = re.split(r'[。！？.!?]', text1)
    sentences2 = re.split(r'[。！？.!?]', text2)

    # 计算句子长度分布
    len_dist1 = [len(s.strip()) for s in sentences1 if s.strip()]
    len_dist2 = [len(s.strip()) for s in sentences2 if s.strip()]

    if not len_dist1 or not len_dist2:
        return 0.0

    # 计算分布相似度
    avg1 = sum(len_dist1) / len(len_dist1)
    avg2 = sum(len_dist2) / len(len_dist2)

    return max(0, 100 - abs(avg1 - avg2) * 2)


def _tokenize_normalized(text: str) -> List[str]:
    """分词（规范化后）"""
    if HAS_JIEBA:
        return list(jieba.cut(text))
    else:
        # 简单分词：按空格和单个字符
        tokens = []
        for word in text.split():
            if len(word) > 1:
                tokens.append(word)
            else:
                # 单字符可能是中文
                tokens.extend(list(word))
        return tokens


# 保持向后兼容的函数
def sequence_similarity(text1: str, text2: str) -> float:
    """序列相似度（向后兼容接口）"""
    result = enhanced_sequence_similarity(text1, text2)
    return result.overall


def cosine_similarity(text1: str, text2: str) -> float:
    """余弦相似度（向后兼容接口）"""
    return cosine_similarity_normalized(text1, text2)


def jaccard_similarity(text1: str, text2: str) -> float:
    """Jaccard相似度（向后兼容接口）"""
    return jaccard_similarity_normalized(text1, text2)
