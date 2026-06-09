"""
模板内容排除模块
Template Content Exclusion Module

自动识别和排除报告模板中的公共内容，提高查重准确性
"""

import re
import zipfile
import io
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import List, Dict, Tuple, Set
from dataclasses import dataclass
from collections import Counter


@dataclass
class TemplatePattern:
    """模板匹配模式"""
    content: str           # 模式内容
    weight: float = 1.0    # 权重（出现频率越高，权重越大）
    pattern_type: str = 'text'  # 类型: text, heading, code


class TemplateExtractor:
    """模板内容提取器"""

    def __init__(self, min_occurrence: int = 3):
        """
        初始化提取器

        Args:
            min_occurrence: 最小出现次数，低于此次数的内容不被视为模板
        """
        self.min_occurrence = min_occurrence

    def extract_from_docx(self, docx_path: Path) -> List[TemplatePattern]:
        """
        从 docx 模板文件中提取内容

        Args:
            docx_path: 模板文件路径

        Returns:
            模板模式列表
        """
        # 读取 docx 内容
        text = self._read_docx(docx_path)

        if not text:
            return []

        # 提取模式
        patterns = []

        # 1. 提取标题模式
        headings = self._extract_headings(text)
        patterns.extend([TemplatePattern(h, weight=2.0, pattern_type='heading') for h in headings])

        # 2. 提取常见句子
        sentences = self._extract_sentences(text)
        patterns.extend([TemplatePattern(s, weight=1.0, pattern_type='text') for s in sentences])

        # 3. 提取表格标题
        table_headers = self._extract_table_headers(text)
        patterns.extend([TemplatePattern(h, weight=1.5, pattern_type='text') for h in table_headers])

        return patterns

    def extract_from_multiple_reports(
        self,
        report_paths: List[Path],
        sample_size: int = 10
    ) -> List[TemplatePattern]:
        """
        从多份报告中分析提取模板内容

        Args:
            report_paths: 报告文件路径列表
            sample_size: 采样数量（分析前N份报告）

        Returns:
            模板模式列表
        """
        # 采样
        samples = report_paths[:sample_size] if len(report_paths) > sample_size else report_paths

        # 收集所有内容
        all_headings = []
        all_sentences = []
        all_code_patterns = []

        for path in samples:
            text = self._read_docx(path)
            if not text:
                continue

            # 提取标题
            headings = self._extract_headings(text)
            all_headings.extend(headings)

            # 提取句子
            sentences = self._extract_sentences(text)
            all_sentences.extend(sentences)

            # 提取代码模式
            code_patterns = self._extract_code_patterns(text)
            all_code_patterns.extend(code_patterns)

        # 统计频率
        patterns = []

        # 标题（出现频率高的是模板）
        heading_counter = Counter(all_headings)
        for heading, count in heading_counter.items():
            if count >= self.min_occurrence:
                patterns.append(TemplatePattern(
                    heading,
                    weight=float(count) / len(samples),
                    pattern_type='heading'
                ))

        # 句子
        sentence_counter = Counter(all_sentences)
        for sentence, count in sentence_counter.items():
            if count >= self.min_occurrence and len(sentence) > 8:
                patterns.append(TemplatePattern(
                    sentence,
                    weight=float(count) / len(samples),
                    pattern_type='text'
                ))

        # 代码模式
        code_counter = Counter(all_code_patterns)
        for code, count in code_counter.items():
            if count >= self.min_occurrence:
                patterns.append(TemplatePattern(
                    code,
                    weight=float(count) / len(samples),
                    pattern_type='code'
                ))

        return patterns

    def _read_docx(self, path: Path) -> str:
        """读取 docx 文件内容"""
        try:
            with open(path, 'rb') as f:
                docx_data = f.read()

            with zipfile.ZipFile(io.BytesIO(docx_data), 'r') as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                texts = []

                for elem in root.iter():
                    if elem.tag.endswith('}t'):
                        if elem.text:
                            texts.append(elem.text)

                return ''.join(texts)
        except Exception as e:
            print(f"Warning: Failed to read {path}: {e}")
            return ''

    def _extract_headings(self, text: str) -> List[str]:
        """提取标题"""
        headings = []

        # 常见标题模式
        patterns = [
            r'([一二三四五六七八九十]+[、．.]\s*[一-龥A-Za-z0-9]+)',
            r'(\d+[、．.]\s*[一-龥A-Za-z0-9]+)',
            r'(实验[目的内容原理步骤结果讨论]+)',
            r'([一二三四五六七八九十]+、)',
            r'(\d+\s*\.\s*[一-龥]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            headings.extend(matches)

        return list(set([h.strip() for h in headings if h.strip()]))

    def _extract_sentences(self, text: str) -> List[str]:
        """提取句子"""
        # 按句号、问号、感叹号分割
        sentences = re.split(r'[。！？\n]', text)

        # 过滤
        filtered = []
        for sent in sentences:
            sent = sent.strip()
            # 长度在 8-50 字符之间
            if 8 <= len(sent) <= 50:
                # 不全是数字或符号
                if not re.match(r'^[\d\s\-\(\)（）]+$', sent):
                    filtered.append(sent)

        return filtered

    def _extract_table_headers(self, text: str) -> List[str]:
        """提取表格标题"""
        # 常见表格标题模式
        patterns = [
            r'(引脚\s*[功能定义说明]+)',
            r'(序号\s*名称\s*[功能说明]+)',
            r'(步骤\s*现象\s*说明)',
            r'(项目\s*内容\s*分值)',
        ]

        headers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            headers.extend(matches)

        return list(set(headers))

    def _extract_code_patterns(self, text: str) -> List[str]:
        """提取代码模式"""
        patterns = []

        # HAL 函数调用模式
        hal_calls = re.findall(r'HAL_GPIO_\w+\([^)]*\)', text)
        patterns.extend(hal_calls)

        # GPIO 常量
        gpio_consts = re.findall(r'GPIO_PIN_\w+', text)
        patterns.extend(gpio_consts)

        # include 语句
        includes = re.findall(r'#include\s*<[^>]+>', text)
        patterns.extend(includes)

        return list(set(patterns))


class TemplateFilter:
    """模板过滤器"""

    def __init__(self, patterns: List[TemplatePattern], threshold: float = 0.5):
        """
        初始化过滤器

        Args:
            patterns: 模板模式列表
            threshold: 匹配阈值（0-1），高于此值被视为模板内容
        """
        self.patterns = patterns
        self.threshold = threshold
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式"""
        self.compiled_patterns = []

        for pattern in self.patterns:
            try:
                # 转义特殊字符
                escaped = re.escape(pattern.content)
                # 允许一定的变化（空格、标点）
                flexible = escaped.replace(r'\ ', r'\s*').replace(r'\，', r'[，、]?\s*')

                regex = re.compile(flexible)
                self.compiled_patterns.append((regex, pattern.weight, pattern.pattern_type))
            except re.error:
                pass

    def is_template_content(self, text: str) -> bool:
        """
        判断文本是否为模板内容

        Args:
            text: 待判断的文本

        Returns:
            是否为模板内容
        """
        if not text or len(text.strip()) < 5:
            return True  # 短内容视为模板

        cleaned = re.sub(r'\s+', '', text)

        # 检查是否匹配任何模式
        for regex, weight, pattern_type in self.compiled_patterns:
            if regex.search(cleaned):
                # 权重越高，越可能是模板
                if weight >= self.threshold:
                    return True

        return False

    def filter_text(self, text: str, return_segments: bool = False) -> str:
        """
        过滤掉模板内容

        Args:
            text: 原始文本
            return_segments: 是否返回分段信息

        Returns:
            过滤后的文本
        """
        # 按段落分割
        paragraphs = re.split(r'\n\n+|\n\s*\n', text)

        filtered = []

        for para in paragraphs:
            if not self.is_template_content(para):
                filtered.append(para)

        return '\n\n'.join(filtered)

    def get_template_ratio(self, text: str) -> float:
        """
        计算文本中模板内容的比例

        Args:
            text: 文本内容

        Returns:
            模板内容占比 (0-1)
        """
        # 按段落分割
        paragraphs = re.split(r'\n\n+|\n\s*\n', text)

        template_count = 0
        total_count = len(paragraphs)

        for para in paragraphs:
            if self.is_template_content(para):
                template_count += 1

        if total_count == 0:
            return 0.0

        return template_count / total_count

    def extract_non_template_segments(self, text: str) -> List[Tuple[str, bool]]:
        """
        提取非模板段落

        Args:
            text: 原始文本

        Returns:
            [(段落内容, 是否为模板), ...]
        """
        # 按段落分割
        paragraphs = re.split(r'(\n\n+|\n\s*\n)', text)

        segments = []

        for i in range(0, len(paragraphs), 2):
            content = paragraphs[i].strip()
            if content:
                is_template = self.is_template_content(content)
                segments.append((content, is_template))

        return segments


def load_template_from_file(template_path: Path) -> TemplateFilter:
    """
    从模板文件加载过滤器

    Args:
        template_path: 模板文件路径

    Returns:
        模板过滤器
    """
    extractor = TemplateExtractor(min_occurrence=2)
    patterns = extractor.extract_from_docx(template_path)

    return TemplateFilter(patterns, threshold=0.3)


def create_filter_from_reports(
    report_paths: List[Path],
    min_occurrence: int = 3,
    threshold: float = 0.4
) -> TemplateFilter:
    """
    从多份报告创建过滤器

    Args:
        report_paths: 报告文件路径列表
        min_occurrence: 最小出现次数
        threshold: 匹配阈值

    Returns:
        模板过滤器
    """
    extractor = TemplateExtractor(min_occurrence=min_occurrence)
    patterns = extractor.extract_from_multiple_reports(report_paths)

    return TemplateFilter(patterns, threshold=threshold)
