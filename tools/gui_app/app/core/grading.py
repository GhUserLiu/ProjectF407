"""
评分评估服务模块

提供评分评估的业务逻辑接口
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import sys

from PyQt6.QtCore import QObject, pyqtSignal

from app.models.domain import ProjectConfig, SubmissionInfo, GradingInfo
from app.utils.workers import GradingWorker

# 添加项目根目录到Python路径
project_root = Path(__file__).parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class GradingService(QObject):
    """评分评估服务"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态描述
    grading_started = pyqtSignal()  # 评分开始
    grading_finished = pyqtSignal(dict)  # 评分完成，携带结果
    grading_failed = pyqtSignal(str)  # 评分失败
    log_message = pyqtSignal(str)  # 日志消息
    student_graded = pyqtSignal(dict)  # 单个学生评分完成

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[GradingWorker] = None
        self._results: Optional[dict] = None

    def start_grading(
        self,
        config: ProjectConfig,
        submissions: Optional[List[SubmissionInfo]] = None
    ) -> None:
        """
        开始评分评估

        Args:
            config: 项目配置
            submissions: 学生提交列表（可选，如果不提供则自动扫描）
        """
        if self._worker and self._worker.isRunning():
            self.log_message.emit("评分正在进行中，请先停止")
            return

        # 准备配置
        grading_config = {
            'experiment_dir': str(config.experiment_dir),
            'experiment_type': config.experiment_type.value,
            'class_name': config.class_name,
            'rubric_path': str(config.rubric_path) if config.rubric_path else None,
            'submissions_dir': str(config.submissions_dir) if config.submissions_dir else None
        }

        # 如果没有提供提交列表，使用None让系统自动扫描
        submissions_list = submissions if submissions else None

        # 创建工作线程
        self._worker = GradingWorker(grading_config, submissions_list)

        # 连接信号
        self._worker.progress_updated.connect(self.progress_updated.emit)
        self._worker.finished.connect(self._on_grading_finished)
        self._worker.error_occurred.connect(self.grading_failed.emit)
        self._worker.log_message.connect(self.log_message.emit)

        # 开始评分
        self.grading_started.emit()
        self._worker.start()

    def stop_grading(self) -> None:
        """停止评分"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self.log_message.emit("正在停止评分...")

    def pause_grading(self) -> None:
        """暂停评分"""
        if self._worker and self._worker.isRunning():
            self._worker.pause()
            self.log_message.emit("评分已暂停")

    def resume_grading(self) -> None:
        """恢复评分"""
        if self._worker and self._worker.isPaused():
            self._worker.resume()
            self.log_message.emit("评分已恢复")

    def is_running(self) -> bool:
        """是否正在评分"""
        return self._worker is not None and self._worker.isRunning()

    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._worker is not None and self._worker.isPaused()

    def get_results(self) -> Optional[dict]:
        """获取评分结果"""
        return self._results

    def get_student_grading(self, student_id: str) -> Optional[GradingInfo]:
        """
        获取指定学生的评分信息

        Args:
            student_id: 学号

        Returns:
            评分信息，如果不存在返回None
        """
        if not self._results:
            return None

        for student_data in self._results.get('students', []):
            if student_data.get('student_id') == student_id:
                return self._parse_student_grading(student_data)

        return None

    def get_grade_distribution(self) -> Dict[str, int]:
        """
        获取等级分布

        Returns:
            等级分布字典 {A: count, B: count, ...}
        """
        if not self._results:
            return {}

        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}

        for student_data in self._results.get('students', []):
            grade = student_data.get('grade', 'F')
            if grade in distribution:
                distribution[grade] += 1

        return distribution

    def get_score_statistics(self) -> Dict[str, float]:
        """
        获取分数统计

        Returns:
            统计信息字典
        """
        if not self._results:
            return {}

        scores = [
            s.get('total_score', 0)
            for s in self._results.get('students', [])
        ]

        if not scores:
            return {}

        return {
            'highest': max(scores),
            'lowest': min(scores),
            'average': sum(scores) / len(scores),
            'count': len(scores)
        }

    def get_all_gradings(self) -> List[GradingInfo]:
        """
        获取所有学生的评分信息

        Returns:
            评分信息列表
        """
        if not self._results:
            return []

        gradings = []
        for student_data in self._results.get('students', []):
            gradings.append(self._parse_student_grading(student_data))

        return gradings

    def _parse_student_grading(self, student_data: dict) -> GradingInfo:
        """解析学生评分数据"""
        return GradingInfo(
            student_id=student_data.get('student_id', ''),
            name=student_data.get('name', ''),
            total_score=student_data.get('total_score', 0.0),
            max_score=student_data.get('max_score', 100.0),
            percentage=student_data.get('percentage', 0.0),
            grade=student_data.get('grade', 'F'),
            strengths=student_data.get('strengths', []),
            weaknesses=student_data.get('weaknesses', []),
            technical_issues=student_data.get('technical_issues', []),
            improvement_suggestions=student_data.get('improvement_suggestions', [])
        )

    def _on_grading_finished(self, results: dict) -> None:
        """评分完成处理"""
        self._results = results
        self.grading_finished.emit(results)
