"""
查重检测服务模块

提供查重检测的业务逻辑接口
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import sys

from PyQt6.QtCore import QObject, pyqtSignal

from app.models.domain import ProjectConfig, SubmissionInfo, PlagiarismPair
from app.utils.workers import PlagiarismWorker

# 添加项目根目录到Python路径
if getattr(sys, 'frozen', False):
    # 如果是打包后的可执行文件，使用 sys._MEIPASS
    meipass = Path(sys._MEIPASS)
    if str(meipass) not in sys.path:
        sys.path.insert(0, str(meipass))
else:
    # 开发环境
    project_root = Path(__file__).parents[4]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


class PlagiarismService(QObject):
    """查重检测服务"""

    # 信号定义
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态描述
    detection_started = pyqtSignal()  # 检测开始
    detection_finished = pyqtSignal(dict)  # 检测完成，携带结果
    detection_failed = pyqtSignal(str)  # 检测失败
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[PlagiarismWorker] = None
        self._results: Optional[dict] = None

    def start_detection(
        self,
        config: ProjectConfig,
        submissions: Optional[List[SubmissionInfo]] = None
    ) -> None:
        """
        开始查重检测

        Args:
            config: 项目配置
            submissions: 学生提交列表（可选，如果不提供则自动扫描）
        """
        # 验证配置
        if not config or not config.submissions_dir:
            self.detection_failed.emit("无效的配置：未设置提交目录")
            return

        submissions_path = Path(config.submissions_dir)
        if not submissions_path.exists():
            self.detection_failed.emit(f"提交目录不存在: {config.submissions_dir}")
            return

        if self._worker and self._worker.isRunning():
            self.log_message.emit("检测正在进行中，请先停止")
            return

        # 准备配置
        detection_config = {
            'experiment_dir': str(config.experiment_dir) if config.experiment_dir else None,
            'experiment_type': config.experiment_type.value if hasattr(config.experiment_type, 'value') else str(config.experiment_type),
            'class_name': config.class_name,
            'suspicious_threshold': config.suspicious_threshold,
            'high_similarity_threshold': config.high_similarity_threshold,
            'plagiarism_threshold': config.plagiarism_threshold,
            'weights': config.weights.to_dict() if hasattr(config.weights, 'to_dict') else {},
            'submissions_dir': str(config.submissions_dir)
        }

        # 如果没有提供提交列表，使用None让系统自动扫描
        submissions_list = submissions if submissions else None

        try:
            # 创建工作线程
            self._worker = PlagiarismWorker(detection_config, submissions_list)

            # 连接信号（使用Qt.DirectConnection确保即时传递）
            self._worker.progress_updated.connect(lambda p, m: self.progress_updated.emit(p, m))
            self._worker.finished.connect(self._on_detection_finished)
            self._worker.error_occurred.connect(lambda e: self.detection_failed.emit(str(e)))
            self._worker.log_message.connect(lambda m: self.log_message.emit(str(m)))

            # 开始检测
            self.detection_started.emit()
            self._worker.start()

        except Exception as e:
            import traceback
            error_msg = f"启动检测失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.detection_failed.emit(error_msg)
            print(traceback.format_exc())

    def stop_detection(self) -> None:
        """停止检测"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self.log_message.emit("正在停止检测...")

    def pause_detection(self) -> None:
        """暂停检测"""
        if self._worker and self._worker.isRunning():
            self._worker.pause()
            self.log_message.emit("检测已暂停")

    def resume_detection(self) -> None:
        """恢复检测"""
        if self._worker and self._worker.isPaused():
            self._worker.resume()
            self.log_message.emit("检测已恢复")

    def is_running(self) -> bool:
        """是否正在检测"""
        return self._worker is not None and self._worker.isRunning()

    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._worker is not None and self._worker.isPaused()

    def get_results(self) -> Optional[dict]:
        """获取检测结果"""
        return self._results

    def get_suspicious_pairs(self) -> List[PlagiarismPair]:
        """
        获取可疑对比对列表

        Returns:
            可疑对比对列表
        """
        if not self._results:
            return []

        suspicious_pairs = []
        results = self._results

        # 从结果中提取可疑对
        for pair_data in results.get('similarity_pairs', []):
            if pair_data.get('overall_similarity', 0) >= 60.0:  # 可疑阈值
                pair = PlagiarismPair(
                    student_id_1=pair_data.get('student_id_1', ''),
                    name_1=pair_data.get('name_1', ''),
                    student_id_2=pair_data.get('student_id_2', ''),
                    name_2=pair_data.get('name_2', ''),
                    overall_similarity=pair_data.get('overall_similarity', 0.0),
                    text_similarity=pair_data.get('text_similarity', 0.0),
                    code_similarity=pair_data.get('code_similarity', 0.0),
                    structure_similarity=pair_data.get('structure_similarity', 0.0),
                    is_cross_group=pair_data.get('is_cross_group', False)
                )
                suspicious_pairs.append(pair)

        return suspicious_pairs

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取检测统计信息

        Returns:
            统计信息字典
        """
        if not self._results:
            return {}

        return {
            'total_students': self._results.get('total_students', 0),
            'total_pairs': self._results.get('total_pairs', 0),
            'suspicious_count': self._results.get('suspicious_count', 0),
            'plagiarism_count': self._results.get('plagiarism_count', 0),
            'max_similarity': self._results.get('max_similarity', 0.0),
            'avg_similarity': self._results.get('avg_similarity', 0.0)
        }

    def _on_detection_finished(self, results: dict) -> None:
        """检测完成处理"""
        self._results = results
        self.detection_finished.emit(results)
