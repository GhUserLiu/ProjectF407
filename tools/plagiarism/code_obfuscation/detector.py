# -*- coding: utf-8 -*-
"""
代码混淆检测器
Code Obfuscation Detector

检测代码混淆情况，如变量重命名、格式调整、注释删除等
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Optional
from enum import Enum


class ObfuscationType(Enum):
    """混淆类型"""
    VARIABLE_RENAMING = 'variable_renaming'     # 变量重命名
    FORMAT_CHANGE = 'format_change'            # 格式调整
    COMMENT_REMOVAL = 'comment_removal'        # 注释删除
    WHITESPACE_CHANGE = 'whitespace_change'    # 空白符变化
    FUNCTION_REORDERING = 'function_reordering'  # 函数重排序


@dataclass
class VariableRenamingResult:
    """变量重命名检测结果"""
    renamed_variables: Dict[str, str]  # 原变量名: 新变量名
    confidence: float                  # 置信度 0-1
    evidence: List[str] = field(default_factory=list)  # 证据列表


@dataclass
class CodeObfuscationResult:
    """代码混淆检测结果"""
    structural_similarity: float       # 结构相似度 0-100
    logic_similarity: float            # 逻辑相似度 0-100
    is_obfuscated: bool                # 是否存在混淆
    obfuscation_types: List[ObfuscationType]  # 混淆类型列表
    evidence: List[Dict]                # 混淆证据
    normalized_similarity: float       # 标准化后相似度 0-100
    details: Dict = field(default_factory=dict)  # 详细信息


class CCodeNormalizer:
    """C代码标准化器"""

    # 变量名模式（通用和STM32相关）
    VARIABLE_PATTERNS = [
        r'\b[a-z_][a-z0-9_]*\b',           # 普通变量（小写开头）
        r'\b[A-Z_][A-Z0-9_]*\b',           # 常量（大写）
        r'\bHAL_[A-Z_]+\b',                # HAL库函数
        r'\bGPIO_[A-Z_]+\b',               # GPIO常量
        r'\bEXTI_[A-Z_]+\b',               # EXTI常量
        r'\b__IO[A-Z_]+\b',                # 寄存器
    ]

    # 函数声明模式
    FUNCTION_PATTERN = r'\b(?:void|int|char|float|double|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t)\s+(\w+)\s*\([^)]*\)\s*{?'

    # 控制流模式
    CONTROL_FLOW_PATTERNS = [
        r'\bif\s*\(',
        r'\belse\b',
        r'\bfor\s*\(',
        r'\bwhile\s*\(',
        r'\bswitch\s*\(',
        r'\bcase\s+\w+',
        r'\bbreak\b',
        r'\bcontinue\b',
        r'\breturn\b',
        r'\bgoto\s+\w+',
    ]

    @staticmethod
    def normalize_code(code: str) -> str:
        """
        标准化代码，去除混淆效果

        Args:
            code: 原始代码

        Returns:
            标准化后的代码
        """
        # 移除注释
        code = CCodeNormalizer._remove_comments(code)

        # 标准化空白符
        code = CCodeNormalizer._normalize_whitespace(code)

        # 标准化变量名（替换为统一格式）
        code = CCodeNormalizer._normalize_variable_names(code)

        return code.strip()

    @staticmethod
    def _remove_comments(code: str) -> str:
        """移除注释"""
        # 移除单行注释
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        # 移除多行注释
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        return code

    @staticmethod
    def _normalize_whitespace(code: str) -> str:
        """标准化空白符"""
        # 将多个空白符替换为单个空格
        code = re.sub(r'\s+', ' ', code)
        # 移除操作符周围不必要的空格
        code = re.sub(r'\s*([{}();,])\s*', r'\1', code)
        # 在特定位置添加空格
        code = re.sub(r'([{}();])', r' \1 ', code)
        # 清理多余空格
        code = re.sub(r'\s+', ' ', code)
        return code

    @staticmethod
    def _normalize_variable_names(code: str) -> str:
        """标准化变量名（用于结构比较，保留控制流）"""
        # 提取所有控制流关键字
        control_flow_keywords = {'if', 'else', 'for', 'while', 'switch', 'case',
                                'break', 'continue', 'return', 'goto', 'void',
                                'int', 'char', 'float', 'double', 'uint8_t',
                                'uint16_t', 'uint32_t', 'int8_t', 'int16_t', 'int32_t'}

        # 替换变量名为统一格式（VAR_0, VAR_1, ...）
        var_counter = 0
        var_map = {}

        def replace_var(match):
            nonlocal var_counter
            var_name = match.group(0)
            if var_name in control_flow_keywords:
                return var_name
            if var_name not in var_map:
                var_map[var_name] = f'VAR_{var_counter}'
                var_counter += 1
            return var_map[var_name]

        # 仅替换小写开头的变量（保留常量、函数名等）
        code = re.sub(r'\b[a-z_][a-z0-9_]{2,}\b', replace_var, code)

        return code

    @staticmethod
    def extract_structure(code: str) -> Dict:
        """
        提取代码结构特征

        Returns:
            结构特征字典
        """
        normalized = CCodeNormalizer.normalize_code(code)

        # 提取函数结构
        functions = re.findall(CCodeNormalizer.FUNCTION_PATTERN, code)

        # 统计控制流
        control_flow = {}
        for pattern in CCodeNormalizer.CONTROL_FLOW_PATTERNS:
            matches = re.findall(pattern, code, re.IGNORECASE)
            keyword = pattern.split()[0].replace('\\', '').replace('(', '').replace('\b', '')
            control_flow[keyword] = len(matches)

        # 提取调用序列
        call_sequence = re.findall(r'(\w+)\s*\(', normalized)
        call_sequence = [c for c in call_sequence if c not in ('if', 'for', 'while', 'switch', 'return')]

        return {
            'function_count': len(functions),
            'functions': functions,
            'control_flow': control_flow,
            'call_sequence': call_sequence,
            'normalized': normalized
        }


class CodeObfuscationDetector:
    """代码混淆检测器"""

    def __init__(self, language: str = 'c'):
        """
        初始化检测器

        Args:
            language: 编程语言 ('c', 'cpp', 'python')
        """
        self.language = language
        if language == 'c':
            self.normalizer = CCodeNormalizer
        # 可以添加其他语言的支持

    def detect(
        self,
        code1: str,
        code2: str,
        deep_check: bool = True
    ) -> CodeObfuscationResult:
        """
        检测代码混淆情况

        Args:
            code1: 第一段代码
            code2: 第二段代码
            deep_check: 是否进行深度检查

        Returns:
            代码混淆检测结果
        """
        # 提取结构特征
        struct1 = self.normalizer.extract_structure(code1)
        struct2 = self.normalizer.extract_structure(code2)

        # 计算结构相似度
        structural_sim = self._calculate_structural_similarity(struct1, struct2)

        # 计算逻辑相似度
        logic_sim = self._calculate_logic_similarity(struct1, struct2)

        # 计算标准化后相似度
        normalized_sim = self._calculate_normalized_similarity(
            struct1['normalized'],
            struct2['normalized']
        )

        # 判断是否混淆
        is_obfuscated, obfuscation_types, evidence = self._detect_obfuscation(
            code1, code2, struct1, struct2, structural_sim, logic_sim
        )

        return CodeObfuscationResult(
            structural_similarity=structural_sim,
            logic_similarity=logic_sim,
            is_obfuscated=is_obfuscated,
            obfuscation_types=obfuscation_types,
            evidence=evidence,
            normalized_similarity=normalized_sim,
            details={
                'struct1': struct1,
                'struct2': struct2
            }
        )

    def detect_variable_renaming(
        self,
        code1: str,
        code2: str
    ) -> VariableRenamingResult:
        """
        检测变量重命名

        Args:
            code1: 第一段代码
            code2: 第二段代码

        Returns:
            变量重命名检测结果
        """
        # 提取变量
        vars1 = self._extract_variables(code1)
        vars2 = self._extract_variables(code2)

        # 比较变量集合
        renamed = {}
        confidence = 0.0
        evidence = []

        if len(vars1) > 0 and len(vars2) > 0:
            # 如果变量名完全不同但数量相同
            if len(vars1 & vars2) == 0 and len(vars1) == len(vars2):
                # 尝试基于使用模式匹配
                confidence = 0.7
                evidence.append("变量名完全不同但数量相同，可能重命名")
            elif len(vars1 & vars2) < len(vars1) * 0.3:
                # 共同变量少于30%，可能部分重命名
                confidence = 0.5
                common = len(vars1 & vars2)
                evidence.append(f"仅有 {common} 个共同变量，可能部分重命名")

        return VariableRenamingResult(
            renamed_variables=renamed,
            confidence=confidence,
            evidence=evidence
        )

    def _extract_variables(self, code: str) -> Set[str]:
        """提取变量名"""
        # 移除注释和字符串
        code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
        code = re.sub(r'".*?"', '', code)

        variables = set()

        # 匹配变量定义和使用
        # 匹配类型定义后的变量
        for match in re.finditer(
            r'\b(?:int|char|float|double|uint8_t|uint16_t|uint32_t)\s+(\w+)',
            code
        ):
            variables.add(match.group(1))

        # 匹配赋值和使用的变量
        for match in re.finditer(r'\b([a-z_][a-z0-9_]{2,})\s*[=;]', code):
            variables.add(match.group(1))

        # 过滤关键字
        keywords = {'if', 'else', 'for', 'while', 'return', 'void', 'struct'}
        variables -= keywords

        return variables

    def _calculate_structural_similarity(
        self,
        struct1: Dict,
        struct2: Dict
    ) -> float:
        """计算结构相似度"""
        score = 0.0
        max_score = 0.0

        # 函数数量相似度
        if struct1['function_count'] == struct2['function_count']:
            score += 30
        elif abs(struct1['function_count'] - struct2['function_count']) <= 1:
            score += 15
        max_score += 30

        # 控制流相似度
        cf1 = struct1['control_flow']
        cf2 = struct2['control_flow']
        all_keys = set(cf1.keys()) | set(cf2.keys())

        if all_keys:
            cf_sim = 0
            for key in all_keys:
                v1 = cf1.get(key, 0)
                v2 = cf2.get(key, 0)
                if v1 == v2:
                    cf_sim += 1
                elif abs(v1 - v2) <= 1:
                    cf_sim += 0.5
            score += (cf_sim / len(all_keys)) * 40
        max_score += 40

        # 调用序列相似度
        seq1 = struct1['call_sequence']
        seq2 = struct2['call_sequence']
        if seq1 and seq2:
            seq_sim = len(set(seq1) & set(seq2)) / len(set(seq1) | set(seq2))
            score += seq_sim * 30
        max_score += 30

        return (score / max_score * 100) if max_score > 0 else 0

    def _calculate_logic_similarity(
        self,
        struct1: Dict,
        struct2: Dict
    ) -> float:
        """计算逻辑相似度"""
        # 基于标准化代码的相似度
        return self._calculate_normalized_similarity(
            struct1['normalized'],
            struct2['normalized']
        )

    def _calculate_normalized_similarity(
        self,
        code1: str,
        code2: str
    ) -> float:
        """计算标准化代码的相似度"""
        from difflib import SequenceMatcher

        return SequenceMatcher(None, code1, code2).ratio() * 100

    def _detect_obfuscation(
        self,
        code1: str,
        code2: str,
        struct1: Dict,
        struct2: Dict,
        structural_sim: float,
        logic_sim: float
    ) -> Tuple[bool, List[ObfuscationType], List[Dict]]:
        """
        检测混淆类型

        Returns:
            (是否混淆, 混淆类型列表, 证据列表)
        """
        obfuscation_types = []
        evidence = []

        # 高结构相似度但低文本相似度 = 可能混淆
        if structural_sim > 70 and logic_sim < 50:
            obfuscation_types.append(ObfuscationType.VARIABLE_RENAMING)
            evidence.append({
                'type': 'variable_renaming',
                'description': '结构相似但代码不同，可能变量重命名'
            })

        # 检测注释删除
        comment_ratio1 = self._calculate_comment_ratio(code1)
        comment_ratio2 = self._calculate_comment_ratio(code2)
        if comment_ratio1 > 0.1 and comment_ratio2 < 0.05:
            obfuscation_types.append(ObfuscationType.COMMENT_REMOVAL)
            evidence.append({
                'type': 'comment_removal',
                'description': f'代码1注释率{comment_ratio1:.1%}，代码2注释率{comment_ratio2:.1%}'
            })

        # 检测空白符变化
        ws_ratio1 = self._calculate_whitespace_ratio(code1)
        ws_ratio2 = self._calculate_whitespace_ratio(code2)
        if abs(ws_ratio1 - ws_ratio2) > 0.1:
            obfuscation_types.append(ObfuscationType.WHITESPACE_CHANGE)
            evidence.append({
                'type': 'whitespace_change',
                'description': f'空白符比例差异较大'
            })

        # 检测格式调整
        if structural_sim > 80 and logic_sim > 60 and logic_sim < 85:
            obfuscation_types.append(ObfuscationType.FORMAT_CHANGE)
            evidence.append({
                'type': 'format_change',
                'description': '结构和逻辑相似但有差异，可能格式调整'
            })

        is_obfuscated = len(obfuscation_types) > 0

        return is_obfuscated, obfuscation_types, evidence

    def _calculate_comment_ratio(self, code: str) -> float:
        """计算注释比例"""
        total_len = len(code)
        if total_len == 0:
            return 0

        # 计算注释长度
        comment_len = 0
        for match in re.finditer(r'//.*?$', code, re.MULTILINE):
            comment_len += match.end() - match.start()
        for match in re.finditer(r'/\*.*?\*/', code, re.DOTALL):
            comment_len += match.end() - match.start()

        return comment_len / total_len

    def _calculate_whitespace_ratio(self, code: str) -> float:
        """计算空白符比例"""
        total_len = len(code)
        if total_len == 0:
            return 0

        ws_len = len(re.findall(r'\s', code))
        return ws_len / total_len
