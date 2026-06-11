"""
增强版实验报告查重与评分系统
Enhanced Plagiarism Detection and Grading System for Lab Reports

提供多种相似度算法、模板排除、代码查重、详细评分、技术检查、可视化报告等功能
v2.5.0 - 新增代码深度分析、智能反馈建议、图像质量检测、评分一致性校验
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
from .unified_feedback import (
    UnifiedFeedbackGenerator,
    UnifiedFeedbackResult,
    FeedbackFormat,
    FeedbackStyle,
    save_unified_feedback,
    generate_feedback
)

# 新增：配置系统
from .config import (
    PlagiarismConfig,
    SimilarityWeights,
    ThresholdConfig,
    FeatureConfig,
    default_config
)

# 新增：高级检测功能
from .code_obfuscation import (
    CodeObfuscationDetector,
    CodeObfuscationResult,
    ObfuscationType
)
from .semantic import (
    SemanticDetector,
    SemanticSimilarityResult,
    SemanticMethod
)
from .comparison_view import (
    ComparisonViewGenerator,
    DiffHighlighter,
    DiffBlock,
    DiffType
)
from .ai_detection.enhanced_detector import (
    EnhancedAIGeneratorDetector,
    AIGenerationResult
)
from .ai_detection.detector import (
    AIGeneratedDetector,
    AIGenerationResult as OldAIGenerationResult
)
from .image_similarity import (
    ImageDetector,
    ImageSimilarityResult,
    HashType
)
from .image_quality import (
    ImageQualityAssessor,
    ImageQualityResult,
    ImageType,
    QualityMetrics,
    ContentAnalyzer,
    LabReportValidator
)

# ========== v2.5.0 新增：质量评估强化 ==========
from .code_analyzer import (
    EnhancedCodeAnalyzer,
    CStyleParser,
    NamingConventionChecker,
    ComplexityAnalyzer,
    BestPracticeChecker,
    SecurityChecker,
    CodeAnalysisResult,
    CodeIssue,
    Severity,
    FunctionMetrics,
    analyze_code_from_report
)
from .smart_feedback import (
    SmartFeedbackEngine,
    SmartFeedback,
    FeedbackCategory,
    LearningResource,
    generate_smart_feedback_report
)
from .image_quality_checker import (
    ImageQualityChecker,
    ImageRelevanceChecker,
    ImageAnalysisResult,
    ImageQuality,
    ImageIssue,
    check_images_from_directory
)
from .grading_validator import (
    GradingValidator,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
    validate_grading_results
)

__version__ = '2.5.0'
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
    'save_student_feedback',
    # 统一反馈系统 (v2.6.0 新增)
    'UnifiedFeedbackGenerator',
    'UnifiedFeedbackResult',
    'FeedbackFormat',
    'FeedbackStyle',
    'save_unified_feedback',
    'generate_feedback',
    # ========== 配置系统 (v2.4.0 新增) ==========
    'PlagiarismConfig',
    'SimilarityWeights',
    'ThresholdConfig',
    'FeatureConfig',
    'default_config',
    # ========== 高级检测功能 ==========
    # 代码混淆检测
    'CodeObfuscationDetector',
    'CodeObfuscationResult',
    'ObfuscationType',
    # 语义相似度检测
    'SemanticDetector',
    'SemanticSimilarityResult',
    'SemanticMethod',
    # 详细对比视图
    'ComparisonViewGenerator',
    'DiffHighlighter',
    'DiffBlock',
    'DiffType',
    # AI生成检测 (增强版)
    'EnhancedAIGeneratorDetector',
    'AIGenerationResult',
    # AI生成检测 (旧版，保持兼容)
    'AIGeneratedDetector',
    # 图片相似度检测
    'ImageDetector',
    'ImageSimilarityResult',
    'HashType',
    # ========== 图片质量评估 ==========
    'ImageQualityAssessor',
    'ImageQualityResult',
    'ImageType',
    'QualityMetrics',
    'ContentAnalyzer',
    'LabReportValidator',
    # ========== v2.5.0 新增：质量评估强化 ==========
    # 代码深度分析
    'EnhancedCodeAnalyzer',
    'CStyleParser',
    'NamingConventionChecker',
    'ComplexityAnalyzer',
    'BestPracticeChecker',
    'SecurityChecker',
    'CodeAnalysisResult',
    'CodeIssue',
    'Severity',
    'FunctionMetrics',
    'analyze_code_from_report',
    # 智能反馈建议
    'SmartFeedbackEngine',
    'SmartFeedback',
    'FeedbackCategory',
    'LearningResource',
    'generate_smart_feedback_report',
    # 图像质量检测
    'ImageQualityChecker',
    'ImageRelevanceChecker',
    'ImageAnalysisResult',
    'ImageQuality',
    'ImageIssue',
    'check_images_from_directory',
    # 评分一致性校验
    'GradingValidator',
    'ValidationIssue',
    'ValidationReport',
    'ValidationSeverity',
    'validate_grading_results',
]

