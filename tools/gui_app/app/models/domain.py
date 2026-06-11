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

    # 提交目录
    submissions_dir: Optional[Path] = None

    # 输出目录
    output_dir: Optional[Path] = None

    # 元数据
    created_at: str = ""
    modified_at: str = ""
    version: str = "1.0.0"

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
