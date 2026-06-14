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

# 设置正确的Python路径
if getattr(sys, 'frozen', False):
    # 打包后的可执行文件环境
    meipass = Path(sys._MEIPASS)
    if str(meipass) not in sys.path:
        sys.path.insert(0, str(meipass))
    # 额外尝试：添加 tools 目录到 sys.path
    tools_dir = meipass / 'tools'
    if tools_dir.exists() and str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
        print(f"[DEBUG] 添加 {tools_dir} 到 sys.path", file=sys.stderr)
else:
    # 开发环境
    project_root = Path(__file__).parents[4]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from app.models.domain import MultiClassProjectConfig

# 尝试导入plagiarism模块，如果失败则使用空实现
PLAGIARISM_AVAILABLE = False
MultiClassDetector = None
MultiClassDetectionResult = None
MultiClassReportGenerator = None

def create_multi_class_config(*args, **kwargs):
    """默认实现：返回空列表"""
    print("[WARNING] 使用默认的 create_multi_class_config 实现（查重模块不可用）", file=sys.stderr)
    return []

try:
    # 添加调试信息
    print(f"[DEBUG] sys.path: {sys.path[:5]}", file=sys.stderr)
    print(f"[DEBUG] 尝试导入 tools.plagiarism.core.multi_class_detector", file=sys.stderr)

    # 尝试直接导入
    from tools.plagiarism.core.multi_class_detector import (
        MultiClassDetector as _MultiClassDetector,
        MultiClassDetectionResult as _MultiClassDetectionResult,
        create_multi_class_config as _create_multi_class_config
    )
    from tools.plagiarism.report.multi_class_report import MultiClassReportGenerator as _MultiClassReportGenerator

    MultiClassDetector = _MultiClassDetector
    MultiClassDetectionResult = _MultiClassDetectionResult
    MultiClassReportGenerator = _MultiClassReportGenerator
    create_multi_class_config = _create_multi_class_config
    PLAGIARISM_AVAILABLE = True
    print("[INFO] 查重模块加载成功", file=sys.stderr)
except ImportError as e:
    # 尝试使用 importlib 动态导入
    print(f"[DEBUG] 直接导入失败，尝试使用 importlib", file=sys.stderr)
    try:
        import importlib.util
        import os

        # 找到 _MEIPASS 中的 tools 模块
        meipass = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path.cwd()

        # 检查 tools/__init__.py 是否存在
        tools_init = meipass / 'tools' / '__init__.py'
        print(f"[DEBUG] 检查 {tools_init}: 存在={tools_init.exists()}", file=sys.stderr)

        # 列出 meipass 目录下的内容
        print(f"[DEBUG] _MEIPASS 内容: {[p.name for p in meipass.iterdir()[:10]]}", file=sys.stderr)

        # 尝试导入 tools 包
        import importlib
        tools_module = importlib.import_module('tools')
        print(f"[DEBUG] 成功导入 tools 模块: {tools_module}", file=sys.stderr)

        # 现在导入子模块
        from tools.plagiarism.core.multi_class_detector import (
            MultiClassDetector as _MultiClassDetector,
            MultiClassDetectionResult as _MultiClassDetectionResult,
            create_multi_class_config as _create_multi_class_config
        )
        from tools.plagiarism.report.multi_class_report import MultiClassReportGenerator as _MultiClassReportGenerator

        MultiClassDetector = _MultiClassDetector
        MultiClassDetectionResult = _MultiClassDetectionResult
        MultiClassReportGenerator = _MultiClassReportGenerator
        create_multi_class_config = _create_multi_class_config
        PLAGIARISM_AVAILABLE = True
        print("[INFO] 查重模块加载成功 (通过 importlib)", file=sys.stderr)
    except Exception as e2:
        PLAGIARISM_AVAILABLE = False
        print(f"[WARNING] importlib 也失败了: {e2}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        print("[WARNING] 多班级功能将不可用", file=sys.stderr)
except Exception as e:
    PLAGIARISM_AVAILABLE = False
    print(f"[ERROR] 加载查重模块时发生错误: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)


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
            # 检查查重模块是否可用
            if not PLAGIARISM_AVAILABLE:
                self.error_occurred.emit("查重模块不可用，无法执行检测")
                return

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

        except ImportError as e:
            self.error_occurred.emit(f"导入查重模块失败: {str(e)}")
        except Exception as e:
            import traceback
            self.error_occurred.emit(f"检测执行失败: {str(e)}")
            print(traceback.format_exc())

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
        print(f"[DEBUG] MultiClassService.discover_classes 开始", file=sys.stderr)
        print(f"[DEBUG] base_dir={base_dir}, semester={semester}", file=sys.stderr)

        if not PLAGIARISM_AVAILABLE:
            print("[ERROR] 查重模块不可用", file=sys.stderr)
            self.detection_failed.emit("查重模块不可用，请确保plagiarism模块已正确安装")
            return []

        try:
            print("[DEBUG] 调用 create_multi_class_config", file=sys.stderr)
            result = create_multi_class_config(
                base_dir=base_dir,
                semester=semester,
                experiment=experiment,
                class_pattern=class_pattern
            )
            print(f"[DEBUG] create_multi_class_config 返回 {len(result)} 个班级", file=sys.stderr)
            return result
        except ImportError as e:
            import traceback
            error_msg = f"导入模块失败: {str(e)}"
            print(f"[ERROR] {error_msg}\n{traceback.format_exc()}", file=sys.stderr)
            self.detection_failed.emit(error_msg)
            return []
        except AttributeError as e:
            import traceback
            error_msg = f"模块属性错误: {str(e)}"
            print(f"[ERROR] {error_msg}\n{traceback.format_exc()}", file=sys.stderr)
            self.detection_failed.emit(error_msg)
            return []
        except Exception as e:
            import traceback
            error_msg = f"发现班级失败: {str(e)}"
            print(f"[ERROR] {error_msg}\n{traceback.format_exc()}", file=sys.stderr)
            self.detection_failed.emit(error_msg)
            return []

    def create_config(
        self,
        project_name: str,
        class_configs: List[Dict],
        suspicious_threshold: float = 60.0,
        plagiarism_threshold: float = 85.0,
        enable_cross_class: bool = True,
        enable_template_filter: bool = True,
        enable_semantic: bool = True,
        enable_code_obfuscation: bool = False
    ) -> MultiClassProjectConfig:
        """
        创建多班级项目配置

        Args:
            project_name: 项目名称
            class_configs: 班级配置列表
            suspicious_threshold: 可疑阈值
            plagiarism_threshold: 抄袭阈值
            enable_cross_class: 是否启用跨班级检测
            enable_template_filter: 是否启用模板过滤
            enable_semantic: 是否启用语义检测
            enable_code_obfuscation: 是否启用代码混淆检测

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
            shared_threshold=suspicious_threshold,
            shared_weights=SimilarityWeights(),
            enable_cross_class_detection=enable_cross_class,
            enable_template_filter=enable_template_filter,
            enable_semantic_detection=enable_semantic,
            enable_code_obfuscation_detection=enable_code_obfuscation,
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

        # 停止并清理旧的 worker
        self._cleanup_worker()

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

        # 连接信号 - 使用槽函数转发
        self._worker.progress_updated.connect(lambda p, m: self.detection_progress.emit(p, m))
        self._worker.detection_completed.connect(self._on_detection_completed)
        self._worker.error_occurred.connect(lambda e: self.detection_failed.emit(e))

        # 启动检测
        self.detection_started.emit()
        self._worker.start()

    def _cleanup_worker(self):
        """清理旧的 worker"""
        if self._worker:
            if self._worker.isRunning():
                self._worker.stop()
                # 等待线程结束，最多5秒
                if not self._worker.wait(5000):
                    # 超时后强制终止
                    self._worker.terminate()
                    self._worker.wait(1000)

            # 断开所有信号连接
            try:
                self._worker.progress_updated.disconnect()
                self._worker.detection_completed.disconnect()
                self._worker.error_occurred.disconnect()
            except Exception:
                pass

            self._worker = None

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
        self._cleanup_worker()
