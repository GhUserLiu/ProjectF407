"""
数据模型定义

定义应用中使用的核心数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum


class ExperimentType(Enum):
    """实验类型枚举"""
    CAR_GEAR = "档位实验"
    TURN_SIGNAL = "转向灯实验"
    PWM_LED = "PWM LED实验"
    UART = "串口通信实验"
    ADC = "ADC采集实验"
    TIMER = "定时器实验"
    CUSTOM = "自定义"


class FeedbackStyle(Enum):
    """反馈风格枚举"""
    STANDARD = "standard"
    DETAILED = "detailed"
    CONCISE = "concise"
    ENCOURAGING = "encouraging"
    TECHNICAL = "technical"


class SimilarityLevel(Enum):
    """相似度等级"""
    NORMAL = "正常"
    SUSPICIOUS = "可疑"
    HIGH_SIMILARITY = "高相似度"
    PLAGIARISM = "抄袭"


@dataclass
class SimilarityWeights:
    """相似度权重配置"""
    text: float = 0.5
    code: float = 0.3
    structure: float = 0.1
    semantic: float = 0.1

    def to_dict(self) -> Dict[str, float]:
        return {
            'text': self.text,
            'code': self.code,
            'structure': self.structure,
            'semantic': self.semantic
        }


@dataclass
class ThresholdConfig:
    """阈值配置"""
    suspicious: float = 60.0
    high_similarity: float = 70.0
    plagiarism: float = 85.0

    def to_dict(self) -> Dict[str, float]:
        return {
            'suspicious': self.suspicious,
            'high_similarity': self.high_similarity,
            'plagiarism': self.plagiarism
        }


@dataclass
class ProjectConfig:
    """项目配置"""
    class_name: str
    experiment_type: ExperimentType
    experiment_dir: Path
    template_path: Optional[Path] = None
    rubric_path: Optional[Path] = None

    # 查重配置
    suspicious_threshold: float = 60.0
    high_similarity_threshold: float = 70.0
    plagiarism_threshold: float = 85.0
    weights: SimilarityWeights = field(default_factory=SimilarityWeights)

    # 提交目录（自动从 experiment_dir 派生）
    submissions_dir: Optional[Path] = None

    # 输出目录（自动从 experiment_dir 派生）
    output_dir: Optional[Path] = None

    # 元数据
    created_at: str = ""
    modified_at: str = ""
    version: str = "2.0.0"

    def get_paths(self):
        """
        获取统一路径配置

        使用 tools.common.ExperimentPaths 获取标准化的目录结构

        Returns:
            ExperimentPaths: 路径配置实例
        """
        try:
            from tools.common import ExperimentPaths
            return ExperimentPaths(experiment_dir=self.experiment_dir)
        except ImportError:
            # 如果 common 模块不可用，回退到简单实现
            class SimplePaths:
                def __init__(self, experiment_dir):
                    self.experiment_dir = experiment_dir
                    self.submissions_dir = experiment_dir / "submissions" / "extracted"
                    self.processed_dir = experiment_dir / "processed"
                    self.results_dir = experiment_dir / "results"
                    self.reports_dir = self.results_dir / "reports"
                    self.feedback_dir = self.results_dir / "feedback"
                    self.grading_dir = self.results_dir / "grading"
                    self.plagiarism_dir = self.results_dir / "plagiarism"

                def plagiarism_json(self):
                    return self.plagiarism_dir / "plagiarism_results.json"

                def grading_json(self):
                    return self.grading_dir / "grading_results.json"

                def evaluations_json(self):
                    return self.processed_dir / "evaluations.json"

                def extracted_content_json(self):
                    return self.processed_dir / "extracted_content.json"

            return SimplePaths(self.experiment_dir)

    def update_derived_paths(self):
        """
        更新派生路径

        根据 experiment_dir 自动设置 submissions_dir 和 output_dir
        用于兼容旧代码
        """
        if not self.submissions_dir:
            self.submissions_dir = self.experiment_dir / "submissions" / "extracted"

        if not self.output_dir:
            self.output_dir = self.experiment_dir / "results"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'class_name': self.class_name,
            'experiment_type': self.experiment_type.value,
            'experiment_dir': str(self.experiment_dir),
            'template_path': str(self.template_path) if self.template_path else None,
            'rubric_path': str(self.rubric_path) if self.rubric_path else None,
            'suspicious_threshold': self.suspicious_threshold,
            'high_similarity_threshold': self.high_similarity_threshold,
            'plagiarism_threshold': self.plagiarism_threshold,
            'weights': self.weights.to_dict(),
            'submissions_dir': str(self.submissions_dir) if self.submissions_dir else None,
            'output_dir': str(self.output_dir) if self.output_dir else None,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectConfig':
        """从字典创建实例"""
        return cls(
            class_name=data['class_name'],
            experiment_type=ExperimentType(data['experiment_type']),
            experiment_dir=Path(data['experiment_dir']),
            template_path=Path(data['template_path']) if data.get('template_path') else None,
            rubric_path=Path(data['rubric_path']) if data.get('rubric_path') else None,
            suspicious_threshold=data.get('suspicious_threshold', 60.0),
            high_similarity_threshold=data.get('high_similarity_threshold', 70.0),
            plagiarism_threshold=data.get('plagiarism_threshold', 85.0),
            weights=SimilarityWeights(**data.get('weights', {})),
            submissions_dir=Path(data['submissions_dir']) if data.get('submissions_dir') else None,
            output_dir=Path(data['output_dir']) if data.get('output_dir') else None,
            created_at=data.get('created_at', ''),
            modified_at=data.get('modified_at', ''),
            version=data.get('version', '1.0.0')
        )

    @classmethod
    def create_from_class_info(cls, class_info: Dict[str, Any]) -> 'ProjectConfig':
        """
        从班级信息字典创建配置

        Args:
            class_info: 班级信息字典，包含:
                - class_name: 班级名称
                - experiment_dir: 实验目录
                - experiment: 实验类型字符串 (如 "07-car-gear")
                - submissions_dir: 提交目录 (可选)

        Returns:
            ProjectConfig: 项目配置实例
        """
        # 映射实验字符串到枚举
        experiment_map = {
            "07-car-gear": ExperimentType.CAR_GEAR,
            "01-turn-signal": ExperimentType.TURN_SIGNAL,
            "02-pwm-led": ExperimentType.PWM_LED,
        }

        experiment_str = class_info.get('experiment', '07-car-gear')
        experiment_type = experiment_map.get(experiment_str, ExperimentType.CAR_GEAR)

        # 如果没有提供submissions_dir，从experiment_dir派生
        submissions_dir = class_info.get('submissions_dir')
        if not submissions_dir:
            experiment_dir = Path(class_info['experiment_dir'])
            submissions_dir = experiment_dir / 'submissions' / 'extracted'
        else:
            submissions_dir = Path(submissions_dir)

        return cls(
            class_name=class_info['class_name'],
            experiment_type=experiment_type,
            experiment_dir=Path(class_info['experiment_dir']),
            submissions_dir=submissions_dir
        )


@dataclass
class SubmissionInfo:
    """学生提交信息"""
    student_id: str
    name: str
    zip_path: Path
    team_number: Optional[str] = None
    extracted_content: Optional[str] = None
    submit_time: Optional[str] = None
    has_report: bool = False
    has_answer_record: bool = False

    # 检测结果
    similarity_score: Optional[float] = None
    similarity_level: Optional[SimilarityLevel] = None

    # 评分结果
    total_score: Optional[float] = None
    grade: Optional[str] = None
    category_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class PlagiarismPair:
    """查重对比对"""
    student_id_1: str
    name_1: str
    student_id_2: str
    name_2: str
    overall_similarity: float
    text_similarity: float
    code_similarity: float
    structure_similarity: float
    is_cross_group: bool = False
    similarity_level: SimilarityLevel = SimilarityLevel.NORMAL

    @property
    def is_suspicious(self) -> bool:
        return self.similarity_level in [SimilarityLevel.SUSPICIOUS,
                                          SimilarityLevel.HIGH_SIMILARITY,
                                          SimilarityLevel.PLAGIARISM]


@dataclass
class GradingDetail:
    """评分详情"""
    category_name: str
    max_score: float
    score: float
    percentage: float
    feedback: str = ""


@dataclass
class GradingInfo:
    """评分信息"""
    student_id: str
    name: str
    total_score: float
    max_score: float
    percentage: float
    grade: str

    # 分类得分
    category_scores: List[GradingDetail] = field(default_factory=list)

    # 优势与不足
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)

    # 技术问题
    technical_issues: List[str] = field(default_factory=list)

    # 改进建议
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class FeedbackInfo:
    """反馈信息"""
    student_id: str
    name: str
    content: str
    style: FeedbackStyle = FeedbackStyle.DETAILED
    format: str = "markdown"  # markdown, html, pdf
    generated_at: str = ""


# ==================== 多班级支持数据模型 ====================

@dataclass
class ClassConfig:
    """单个班级配置"""
    class_id: str                    # 班级唯一标识
    class_name: str                  # 班级显示名称
    experiment_dir: Path             # 实验目录
    experiment_type: ExperimentType  # 实验类型
    submissions_dir: Optional[Path] = None
    template_path: Optional[Path] = None

    # 统计信息（运行时计算）
    student_count: int = 0
    submission_count: int = 0
    avg_score: float = 0.0
    suspicious_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'class_id': self.class_id,
            'class_name': self.class_name,
            'experiment_dir': str(self.experiment_dir),
            'experiment_type': self.experiment_type.value,
            'submissions_dir': str(self.submissions_dir) if self.submissions_dir else None,
            'template_path': str(self.template_path) if self.template_path else None,
            'student_count': self.student_count,
            'submission_count': self.submission_count,
            'avg_score': self.avg_score,
            'suspicious_rate': self.suspicious_rate
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ClassConfig':
        """从字典创建实例"""
        return cls(
            class_id=data['class_id'],
            class_name=data['class_name'],
            experiment_dir=Path(data['experiment_dir']),
            experiment_type=ExperimentType(data['experiment_type']),
            submissions_dir=Path(data['submissions_dir']) if data.get('submissions_dir') else None,
            template_path=Path(data['template_path']) if data.get('template_path') else None,
            student_count=data.get('student_count', 0),
            submission_count=data.get('submission_count', 0),
            avg_score=data.get('avg_score', 0.0),
            suspicious_rate=data.get('suspicious_rate', 0.0)
        )


@dataclass
class MultiClassProjectConfig:
    """多班级项目配置"""
    project_id: str                  # 项目唯一标识
    project_name: str                 # 项目名称
    classes: List[ClassConfig]       # 班级列表

    # 共享配置
    shared_threshold: float = 60.0           # 可疑阈值
    shared_weights: SimilarityWeights = field(default_factory=SimilarityWeights)
    enable_cross_class_detection: bool = True  # 是否启用跨班级检测

    # 高级检测选项
    enable_template_filter: bool = True       # 启用模板过滤
    enable_semantic_detection: bool = True    # 启用语义检测
    enable_code_obfuscation_detection: bool = False  # 启用代码混淆检测

    # 输出配置
    output_dir: Optional[Path] = None

    # 元数据
    created_at: str = ""
    modified_at: str = ""
    version: str = "2.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            'project_id': self.project_id,
            'project_name': self.project_name,
            'classes': [c.to_dict() for c in self.classes],
            'shared_threshold': self.shared_threshold,
            'shared_weights': self.shared_weights.to_dict(),
            'enable_cross_class_detection': self.enable_cross_class_detection,
            'enable_template_filter': self.enable_template_filter,
            'enable_semantic_detection': self.enable_semantic_detection,
            'enable_code_obfuscation_detection': self.enable_code_obfuscation_detection,
            'output_dir': str(self.output_dir) if self.output_dir else None,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'version': self.version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MultiClassProjectConfig':
        """从字典反序列化"""
        return cls(
            project_id=data['project_id'],
            project_name=data['project_name'],
            classes=[ClassConfig.from_dict(c) for c in data['classes']],
            shared_threshold=data.get('shared_threshold', 60.0),
            shared_weights=SimilarityWeights(**data.get('shared_weights', {})),
            enable_cross_class_detection=data.get('enable_cross_class_detection', True),
            enable_template_filter=data.get('enable_template_filter', True),
            enable_semantic_detection=data.get('enable_semantic_detection', True),
            enable_code_obfuscation_detection=data.get('enable_code_obfuscation_detection', False),
            output_dir=Path(data['output_dir']) if data.get('output_dir') else None,
            created_at=data.get('created_at', ''),
            modified_at=data.get('modified_at', ''),
            version=data.get('version', '2.0.0')
        )


@dataclass
class CrossClassComparison:
    """跨班级对比结果"""
    class_id_1: str
    class_name_1: str
    class_id_2: str
    class_name_2: str

    # 对比指标
    avg_similarity: float           # 平均相似度
    max_similarity: float           # 最高相似度
    suspicious_pairs: int           # 可疑对数
    cross_class_pairs: int          # 跨班级对数

    # 质量对比
    avg_score_diff: float           # 平均分差异
    submission_rate_diff: float    # 提交率差异

    # 时间戳
    compared_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'class_id_1': self.class_id_1,
            'class_name_1': self.class_name_1,
            'class_id_2': self.class_id_2,
            'class_name_2': self.class_name_2,
            'avg_similarity': self.avg_similarity,
            'max_similarity': self.max_similarity,
            'suspicious_pairs': self.suspicious_pairs,
            'cross_class_pairs': self.cross_class_pairs,
            'avg_score_diff': self.avg_score_diff,
            'submission_rate_diff': self.submission_rate_diff,
            'compared_at': self.compared_at
        }
