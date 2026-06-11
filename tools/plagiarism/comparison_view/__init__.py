# -*- coding: utf-8 -*-
"""
详细对比视图模块
Comparison View Module

生成并排高亮相似内容的HTML视图
"""

from .generator import ComparisonViewGenerator
from .diff_highlighter import DiffHighlighter, DiffBlock, DiffType

__all__ = [
    'ComparisonViewGenerator',
    'DiffHighlighter',
    'DiffBlock',
    'DiffType',
]
