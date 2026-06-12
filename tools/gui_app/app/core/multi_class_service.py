"""
多班级处理服务
Multi-Class Processing Service

提供多班级查重检测的后台服务功能
"""

import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal, QThread

from app.models.domain import MultiClassProjectConfig

# 尝试导入plagiarism模块，如果失败则使用空实现
try:
    from tools.plagiarism.core.multi_class_detector import (
        MultiClassDetector,
        MultiClassDetectionResult,
        create_multi_class_config
    )
    from tools.plagiarism.report.multi_class_report import MultiClassReportGenerator
    PLAGIARISM_AVAILABLE = True
except ImportError:
    PLAGIARISM_AVAILABLE = False
    # 创建空实现类以避免导入错误
    class MultiClassDetector:
        def __init__(self, *args, **kwargs):
            pass
    class MultiClassDetectionResult:
        pass
    def create_multi_class_config(*args, **kwargs):
        return []
    class MultiClassReportGenerator:
        def __init__(self, *args, **kwargs):
            pass
        def load_grading_data(self, *args):
            pass
        def generate_all(self, *args, **kwargs):
            return []


class MultiClassWorker(QThread):
    """多班级检测工作线程"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态描述
    detection_completed = pyqtSignal(object)  # MultiClassDetectionResult
    error_occurred = pyqtSignal(str)  # 错误信息

    def __init__(self, class_configs: List[Dict], threshold: float = 60.0, enable_cross_class: bool = True):
        super().__init__()
        self.class_configs = class_configs
        self.threshold = threshold
        self.enable_cross_class = enable_cross_class
        self._is_running = True

    def run(self):
        """执行检测"""
        try:
            # 导入相似度方法
            from tools.plagiarism.core.detector import SimilarityMethod
            method = SimilarityMethod.HYBRID

            # 创建检测器
            detector = MultiClassDetector(
                class_configs=self.class_configs,
                threshold=self.threshold,
                method=method,
                enable_cross_class=self.enable_cross_class,
                progress_callback=lambda p, m: self.progress_updated.emit(p, m) if self._is_running else None
            )

            # 执行检测
            results = detector.detect_all()

            if self._is_running:
                self.detection_completed.emit(results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        """停止检测"""
        self._is_running = False


class MultiClassService(QObject):
    """多班级处理服务"""

    # 信号定义
    detection_started = pyqtSignal()
    detection_progress = pyqtSignal(int, str)
    detection_completed = pyqtSignal(object)  # MultiClassDetectionResult
    detection_failed = pyqtSignal(str)
    report_generated = pyqtSignal(list)  # List[Path]

    def __init__(self):
        super().__init__()
        self._worker: Optional[MultiClassWorker] = None
        self._config: Optional[MultiClassProjectConfig] = None
        self._results: Optional[MultiClassDetectionResult] = None

    def discover_classes(
        self,
        base_dir: Path,
        semester: str = "2026-春季",
        experiment: str = "07-car-gear",
        class_pattern: str = "*班"
    ) -> List[Dict]:
        """
        自动发现班级

        Returns:
            班级配置列表
        """
        if not PLAGIARISM_AVAILABLE:
            self.detection_failed.emit("查重模块不可用，请确保plagiarism模块已正确安装")
            return []

        return create_multi_class_config(
            base_dir=base_dir,
            semester=semester,
            experiment=experiment,
            class_pattern=class_pattern
        )

    def create_config(
        self,
        project_name: str,
        class_configs: List[Dict],
        threshold: float = 60.0,
        enable_cross_class: bool = True
    ) -> MultiClassProjectConfig:
        """
        创建多班级项目配置

        Args:
            project_name: 项目名称
            class_configs: 班级配置列表
            threshold: 相似度阈值
            enable_cross_class: 是否启用跨班级检测

        Returns:
            多班级项目配置
        """
        from app.models.domain import MultiClassProjectConfig, SimilarityWeights

        # 生成项目ID
        project_id = f"{datetime.now().strftime('%Y%m%d')}_{hash(project_name) & 0x7fffffff}"

        return MultiClassProjectConfig(
            project_id=project_id,
            project_name=project_name,
            classes=[],
            shared_threshold=threshold,
            shared_weights=SimilarityWeights(),
            enable_cross_class_detection=enable_cross_class,
            output_dir=Path.cwd() / "multi_class_results" / project_id,
            created_at=datetime.now().isoformat()
        )

    def start_detection(self, config: MultiClassProjectConfig):
        """
        启动检测

        Args:
            config: 多班级项目配置
        """
        if not PLAGIARISM_AVAILABLE:
            self.detection_failed.emit("查重模块不可用，无法执行检测")
            return

        self._config = config

        # 准备班级配置
        class_configs = []
        for class_config in config.classes:
            class_configs.append({
                'class_id': class_config.class_id,
                'class_name': class_config.class_name,
                'submissions_dir': str(class_config.submissions_dir),
                'experiment_dir': str(class_config.experiment_dir)
            })

        # 创建工作线程
        self._worker = MultiClassWorker(
            class_configs=class_configs,
            threshold=config.shared_threshold,
            enable_cross_class=config.enable_cross_class_detection
        )

        # 连接信号
        self._worker.progress_updated.connect(self.detection_progress.emit)
        self._worker.detection_completed.connect(self._on_detection_completed)
        self._worker.error_occurred.connect(self.detection_failed.emit)

        # 启动检测
        self.detection_started.emit()
        self._worker.start()

    def _on_detection_completed(self, results: MultiClassDetectionResult):
        """检测完成处理"""
        self._results = results
        self.detection_completed.emit(results)

    def generate_reports(self, output_dir: Path, formats: List[str] = None) -> List[Path]:
        """
        生成报告

        Args:
            output_dir: 输出目录
            formats: 报告格式列表

        Returns:
            生成的报告路径列表
        """
        if not self._results:
            return []

        if formats is None:
            formats = ['excel', 'json']

        # 创建报告生成器
        report_gen = MultiClassReportGenerator(
            output_dir=output_dir,
            project_name=self._config.project_name
        )

        # 加载评分数据
        class_configs = []
        for class_config in self._config.classes:
            class_configs.append({
                'class_id': class_config.class_id,
                'experiment_dir': class_config.experiment_dir
            })
        report_gen.load_grading_data(class_configs)

        # 生成报告
        report_paths = report_gen.generate_all(self._results, formats=formats)

        self.report_generated.emit(report_paths)
        return report_paths

    def get_results(self) -> Optional[MultiClassDetectionResult]:
        """获取检测结果"""
        return self._results

    def stop_detection(self):
        """停止检测"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait()
