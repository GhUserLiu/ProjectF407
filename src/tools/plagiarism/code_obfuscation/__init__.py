# -*- coding: utf-8 -*-
"""
代码混淆检测模块
Code Obfuscation Detection Module

用于检测代码混淆情况，如变量重命名、格式调整、注释删除等
"""

from .detector import (
    CodeObfuscationDetector,
    CodeObfuscationResult,
    VariableRenamingResult,
    ObfuscationType
)

__all__ = [
    'CodeObfuscationDetector',
    'CodeObfuscationResult',
    'VariableRenamingResult',
    'ObfuscationType',
]
