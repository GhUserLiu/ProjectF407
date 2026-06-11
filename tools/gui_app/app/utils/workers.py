"""
工作线程模块

提供在后台线程执行耗时任务的工作线程类
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, Callable, Any
import sys
from pathlib import Path


# 添加项目根目录到Python路径，以便导入tools模块
project_root = Path(__file__).parents[4]  # 回退到项目根目录
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class BaseWorker(QThread):
    """基础工作线程"""

    # 通用信号
    progress_updated = pyqtSignal(int, str)  # 进度百分比, 状态描述
    finished = pyqtSignal(object)  # 完成信号，携带结果
    error_occurred = pyqtSignal(str)  # 错误信号
    log_message = pyqtSignal(str)  # 日志消息

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_running = True
        self._is_paused = False

    def stop(self):
        """停止工作"""
        self._is_running = False

    def pause(self):
        """暂停工作"""
        self._is_paused = True

    def resume(self):
        """恢复工作"""
        self._is_paused = False

    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    def is_paused(self) -> bool:
        """是否已暂停"""
        return self._is_paused


class PlagiarismWorker(BaseWorker):
    """查重检测工作线程"""

    finished = pyqtSignal(dict)  # 查重结果

    def __init__(self, config: dict, submissions: list, parent=None):
        super().__init__(parent)
        self.config = config
        self.submissions = submissions
        self.results = None

    def run(self):
        """执行查重检测"""
        try:
            self.log_message.emit("开始查重检测...")
            self.progress_updated.emit(5, "初始化检测系统...")

            # 动态导入查重模块
            from tools.plagiarism_detection_enhanced import EnhancedPlagiarismSystem

            self.progress_updated.emit(10, "加载提交内容...")

            # 创建检测系统
            system = EnhancedPlagiarismSystem(
                experiment_dir=self.config.get('experiment_dir'),
                experiment_type=self.config.get('experiment_type', '自定义'),
                class_name=self.config.get('class_name', ''),
                threshold=self.config.get('suspicious_threshold', 60.0),
                config=self._create_plagiarism_config()
            )

            self.progress_updated.emit(30, "执行查重检测...")

            # 执行检测
            self.results = system.run_detection()

            self.progress_updated.emit(90, "生成报告...")

            # 完成检测
            self.progress_updated.emit(100, "查重检测完成")
            self.finished.emit(self.results)
            self.log_message.emit("查重检测完成")

        except Exception as e:
            import traceback
            error_msg = f"查重检测失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            print(traceback.format_exc())

    def _create_plagiarism_config(self):
        """创建查重配置"""
        from tools.plagiarism.config import PlagiarismConfig, SimilarityWeights, ThresholdConfig

        weights = self.config.get('weights', {})
        thresholds = self.config.get('thresholds', {})

        return PlagiarismConfig(
            weights=SimilarityWeights(
                text=weights.get('text', 0.5),
                code=weights.get('code', 0.3),
                structure=weights.get('structure', 0.1),
                semantic=weights.get('semantic', 0.1)
            ),
            thresholds=ThresholdConfig(
                suspicious=self.config.get('suspicious_threshold', 60.0),
                high_similarity=self.config.get('high_similarity_threshold', 70.0),
                plagiarism=self.config.get('plagiarism_threshold', 85.0)
            )
        )


class GradingWorker(BaseWorker):
    """评分评估工作线程"""

    finished = pyqtSignal(dict)  # 评分结果

    def __init__(self, config: dict, submissions: list, parent=None):
        super().__init__(parent)
        self.config = config
        self.submissions = submissions
        self.results = None

    def run(self):
        """执行评分评估"""
        try:
            self.log_message.emit("开始评分评估...")
            self.progress_updated.emit(5, "初始化评分系统...")

            # 动态导入评分模块
            from tools.enhanced_quality_assessment import EnhancedQualityAssessmentSystem

            self.progress_updated.emit(10, "加载提交内容...")

            # 创建评分系统
            system = EnhancedQualityAssessmentSystem(
                experiment_dir=self.config.get('experiment_dir'),
                experiment_type=self.config.get('experiment_type', '自定义'),
                class_name=self.config.get('class_name', ''),
                rubric_path=self.config.get('rubric_path')
            )

            self.progress_updated.emit(30, "执行评分评估...")

            # 执行评分
            self.results = system.run_assessment()

            self.progress_updated.emit(90, "生成报告...")

            # 完成评分
            self.progress_updated.emit(100, "评分评估完成")
            self.finished.emit(self.results)
            self.log_message.emit("评分评估完成")

        except Exception as e:
            import traceback
            error_msg = f"评分评估失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            print(traceback.format_exc())


class FeedbackWorker(BaseWorker):
    """反馈生成工作线程"""

    finished = pyqtSignal(dict)  # 反馈生成结果
    item_completed = pyqtSignal(str, str)  # 学生ID, 反馈内容

    def __init__(self, config: dict, grading_results: dict, style: str = 'detailed', parent=None):
        super().__init__(parent)
        self.config = config
        self.grading_results = grading_results
        self.style = style
        self.results = {}

    def run(self):
        """执行反馈生成"""
        try:
            self.log_message.emit("开始生成反馈...")

            # 动态导入反馈模块
            from tools.plagiarism.unified_feedback import UnifiedFeedbackGenerator

            generator = UnifiedFeedbackGenerator()

            total_students = len(self.grading_results.get('students', []))
            completed = 0

            for student in self.grading_results.get('students', []):
                if not self._is_running:
                    break

                student_id = student.get('student_id')
                student_name = student.get('name')

                self.progress_updated.emit(
                    int(completed / total_students * 100),
                    f"正在为 {student_name} 生成反馈..."
                )

                # 生成反馈
                feedback = generator.generate_feedback(
                    student_info=student,
                    grading_info=self.grading_results,
                    style=self.style
                )

                self.results[student_id] = feedback
                self.item_completed.emit(student_id, feedback)

                completed += 1

            self.progress_updated.emit(100, "反馈生成完成")
            self.finished.emit(self.results)
            self.log_message.emit("反馈生成完成")

        except Exception as e:
            import traceback
            error_msg = f"反馈生成失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            print(traceback.format_exc())


class ReportWorker(BaseWorker):
    """报告生成工作线程"""

    finished = pyqtSignal(str)  # 生成的文件路径

    def __init__(self, report_type: str, data: dict, output_path: str, parent=None):
        super().__init__(parent)
        self.report_type = report_type
        self.data = data
        self.output_path = output_path

    def run(self):
        """执行报告生成"""
        try:
            self.log_message.emit(f"开始生成{self.report_type}报告...")
            self.progress_updated.emit(10, "准备数据...")

            if self.report_type == 'excel':
                self._generate_excel_report()
            elif self.report_type == 'pdf':
                self._generate_pdf_report()
            elif self.report_type == 'html':
                self._generate_html_report()

            self.progress_updated.emit(100, "报告生成完成")
            self.finished.emit(self.output_path)
            self.log_message.emit(f"报告已保存到: {self.output_path}")

        except Exception as e:
            import traceback
            error_msg = f"报告生成失败: {str(e)}"
            self.log_message.emit(error_msg)
            self.error_occurred.emit(error_msg)
            print(traceback.format_exc())

    def _generate_excel_report(self):
        """生成Excel报告"""
        from tools.generate_grading_excel import GradeReportGenerator

        generator = GradeReportGenerator()
        generator.generate_report(
            grading_data=self.data,
            output_path=self.output_path
        )

    def _generate_pdf_report(self):
        """生成PDF报告"""
        # TODO: 实现PDF生成
        pass

    def _generate_html_report(self):
        """生成HTML报告"""
        # TODO: 实现HTML生成
        pass
