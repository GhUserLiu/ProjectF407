"""
增强版实验报告查重与评分系统
Enhanced Plagiarism Detection and Grading System for Lab Reports

提供多种相似度算法、模板排除、代码查重、详细评分、技术检查、可视化报告等功能
"""

from .core import (
    PlagiarismDetector,
    TextPreprocessor,
    SimilarityResult,
    SimilarityMethod
)
from .algorithms import (
    sequence_similarity,
    cosine_similarity,
    jaccard_similarity,
    levenshtein_similarity,
    compute_similarity
)
from .report import (
    PlagiarismReport,
    SimilarityMatrix,
    ReportConfig
)
from .grading import (
    RubricLoader,
    RubricGrader,
    GradingResult,
    batch_grade,
    load_rubric_for_experiment
)
from .technical_checks import (
    TechnicalChecker,
    ExperimentType,
    CheckResult,
    ContentStructureChecker,
    CodeSnippetChecker,
    ThinkingQuestionsChecker
)
from .feedback import (
    FeedbackGenerator,
    HTMLFeedbackGenerator,
    save_student_feedback
)

__version__ = '2.1.0'
__all__ = [
    # 核心
    'PlagiarismDetector',
    'TextPreprocessor',
    'SimilarityResult',
    'SimilarityMethod',
    # 算法
    'sequence_similarity',
    'cosine_similarity',
    'jaccard_similarity',
    'levenshtein_similarity',
    'compute_similarity',
    # 报告
    'PlagiarismReport',
    'SimilarityMatrix',
    'ReportConfig',
    # 评分
    'RubricLoader',
    'RubricGrader',
    'GradingResult',
    'batch_grade',
    'load_rubric_for_experiment',
    # 技术检查
    'TechnicalChecker',
    'ExperimentType',
    'CheckResult',
    'ContentStructureChecker',
    'CodeSnippetChecker',
    'ThinkingQuestionsChecker',
    # 反馈
    'FeedbackGenerator',
    'HTMLFeedbackGenerator',
    'save_student_feedback'
]
