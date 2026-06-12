"""
评分系统模块
Grading System Module

提供基于 Rubric 的评分功能
"""

# 延迟导入以避免循环导入
def __getattr__(name):
    if name == 'RubricLoader':
        from .grading import RubricLoader
        return RubricLoader
    elif name == 'RubricGrader':
        from .grading import RubricGrader
        return RubricGrader
    elif name == 'batch_grade':
        from .grading import batch_grade
        return batch_grade
    elif name == 'load_rubric_for_experiment':
        from .grading import load_rubric_for_experiment
        return load_rubric_for_experiment
    elif name == 'GradingResult':
        from .grading import GradingResult
        return GradingResult
    elif name == 'EnhancedGradingSystem':
        from .enhanced_grading import EnhancedGradingEngine as EnhancedGradingSystem
        return EnhancedGradingSystem
    elif name == 'EnhancedGradingEngine':
        from .enhanced_grading import EnhancedGradingEngine
        return EnhancedGradingEngine
    elif name == 'GradingValidator':
        from .grading_validator import GradingValidator
        return GradingValidator
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    'RubricLoader',
    'RubricGrader',
    'EnhancedGradingSystem',
    'EnhancedGradingEngine',
    'GradingValidator',
    'batch_grade',
    'load_rubric_for_experiment',
    'GradingResult',
]
