"""
查重检测核心模块
Core Plagiarism Detection Module

提供文本/代码相似度检测的核心功能
"""

from .detector import (
    PlagiarismDetector,
    SimilarityResult,
    SimilarityMethod,
    TextPreprocessor
)

__all__ = [
    'PlagiarismDetector',
    'SimilarityResult',
    'SimilarityMethod',
    'TextPreprocessor',
]
