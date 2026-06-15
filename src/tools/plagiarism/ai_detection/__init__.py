# -*- coding: utf-8 -*-
"""
AI生成内容检测模块
AI Generated Content Detection Module

基于统计特征检测AI生成的内容
"""

from .detector import (
    AIGeneratedDetector,
    AIGenerationResult
)

__all__ = [
    'AIGeneratedDetector',
    'AIGenerationResult',
]
