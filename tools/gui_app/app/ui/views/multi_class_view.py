"""
多班级处理视图

提供多班级查重检测的用户界面
"""

from pathlib import Path
from typing import Optional, List, Dict
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QCheckBox,
    QComboBox, QSplitter, QTextEdit, QFrame, QGridLayout,
    QScrollArea, QSpinBox, QTabWidget, QLineEdit, QSlider,
    QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QBrush

# 注意：不要在这里修改 sys.path，因为 main.py 已经处理了
# 路径设置应该只在 main.py 中进行

from app.models.domain import MultiClassProjectConfig, ClassConfig, CrossClassComparison
from app.ui.file_dialog_utils import get_existing_directory

# 延迟导入 MultiClassService 以避免启动时的导入错误
# 我们将在第一次使用时再导入


class MultiClassView(QWidget):
    """多班级处理视图"""

    # 信号
    status_changed = pyqtSignal(str)
    class_selected = pyqtSignal(str)  # 班级ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[MultiClassProjectConfig] = None
        self.discovered_classes: List[Dict] = []
        self.selected_class_id: Optional[str] = None

        # 设置默认基础路径
        self._setup_default_base_path()

        # 延迟导入 MultiClassService 以避免启动时的导入错误
        try:
            from app.core.multi_class_service import MultiClassService
            self.multi_class_service = MultiClassService()
            self._service_available = True
        except Exception as e:
            print(f"[WARNING] MultiClassService 初始化失败: {e}", file=sys.stderr)
            self.multi_class_service = None
            self._service_available = False

        self._init_ui()
        self._connect_signals()

    def _setup_default_base_path(self):
        """设置默认基础路径"""
        self.base_path = None
        try:
            from app.ui.file_dialog_utils import DialogStartDir
            import sys

            install_dir = DialogStartDir._get_install_dir()
            data_dir = DialogStartDir._get_data_dir()

            print(f"[DEBUG] _setup_default_base_path:", file=sys.stderr)
            print(f"[DEBUG]   install_dir={install_dir}", file=sys.stderr)
            print(f"[DEBUG]   data_dir={data_dir}", file=sys.stderr)
            print(f"[DEBUG]   sys.frozen={getattr(sys, 'frozen', False)}", file=sys.stderr)
            print(f"[DEBUG]   sys._MEIPASS={getattr(sys, '_MEIPASS', 'N/A')}", file=sys.stderr)

            if install_dir:
                # 尝试多种可能的教学目录位置
                possible_dirs = []

                # 开发环境: 项目根目录/docs/teaching
                if (install_dir / 'docs' / 'teaching').exists():
                    possible_dirs.append(install_dir / 'docs' / 'teaching')

                # 打包环境: data/teaching_demo (在 _MEIPASS/data 或 install_dir/data 下)
                if data_dir:
                    if (data_dir / 'teaching_demo').exists():
                        possible_dirs.append(data_dir / 'teaching_demo')
                    if (data_dir / 'teaching').exists():
                        possible_dirs.append(data_dir / 'teaching')

                # 或者直接在 install_dir 下
                if (install_dir / 'teaching_demo').exists():
                    possible_dirs.append(install_dir / 'teaching_demo')
                if (install_dir / 'teaching').exists():
                    possible_dirs.append(install_dir / 'teaching')

                # 其他可能性
                possible_dirs.extend([
                    install_dir / 'data' / 'teaching' if (install_dir / 'data' / 'teaching').exists() else None,
                ])

                # 过滤掉 None
                possible_dirs = [d for d in possible_dirs if d is not None]

                print(f"[DEBUG] 尝试的路径: {[str(d) for d in possible_dirs]}", file=sys.stderr)

                for dir_path in possible_dirs:
                    if dir_path.exists():
                        # 验证该目录下是否有学期目录或班级目录
                        semester_dirs = ['2026-春季', '2025-秋季', '2025-春季']
                        has_semester = any((dir_path / s).exists() for s in semester_dirs)
                        has_classes = any(dir_path.glob('*班'))
                        print(f"[DEBUG] 检查 {dir_path}: has_semester={has_semester}, has_classes={has_classes}", file=sys.stderr)
                        if has_semester or has_classes:
                            self.base_path = dir_path
                            print(f"[INFO] 默认基础路径: {self.base_path}", file=sys.stderr)
                            return

                print(f"[WARNING] 未找到包含学期目录的教学目录", file=sys.stderr)
        except Exception as e:
            print(f"[WARNING] 设置默认路径失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 顶部配置区域
        self._create_config_section(layout)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：班级列表和检测控制
        left_widget = self._create_left_section()
        splitter.addWidget(left_widget)

        # 右侧：详情和结果
        right_widget = self._create_right_section()
        splitter.addWidget(right_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

        # 更新默认路径显示
        self._update_base_path_label()

    def _update_base_path_label(self):
        """更新基础路径标签"""
        if self.base_path and self.base_path.exists():
            self.base_path_label.setText(str(self.base_path))
        else:
            self.base_path_label.setText("未选择")

    def _create_config_section(self, parent_layout):
        """创建配置区域"""
        group = QGroupBox("多班级检测配置")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 5px;
                color: #495057;
            }
        """)

        layout = QHBoxLayout(group)

        # 基础路径配置
        path_layout = QVBoxLayout()
        path_label = QLabel("基础路径:")
        self.base_path_label = QLabel("未选择")
        self.base_path_label.setStyleSheet("color: #6c757d; padding: 5px;")
        path_btn = QPushButton("📂 选择教学目录")
        path_btn.clicked.connect(self._on_select_base_path)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.base_path_label)
        path_layout.addWidget(path_btn)

        layout.addLayout(path_layout)

        # 学期和实验选择
        selection_layout = QGridLayout()

        # 学期选择
        selection_layout.addWidget(QLabel("学期:"), 0, 0)
        self.semester_combo = QComboBox()
        self.semester_combo.addItem("2026-春季", "2026-春季")
        self.semester_combo.addItem("2025-秋季", "2025-秋季")
        self.semester_combo.addItem("2025-春季", "2025-春季")
        selection_layout.addWidget(self.semester_combo, 0, 1)

        # 实验选择
        selection_layout.addWidget(QLabel("实验:"), 1, 0)
        self.experiment_combo = QComboBox()
        self.experiment_combo.addItem("07-car-gear (档位实验)", "07-car-gear")
        self.experiment_combo.addItem("01-turn-signal (转向灯)", "01-turn-signal")
        selection_layout.addWidget(self.experiment_combo, 1, 1)

        # 班级模式
        selection_layout.addWidget(QLabel("班级模式:"), 2, 0)
        self.class_pattern_input = QLineEdit("*班")
        self.class_pattern_input.setPlaceholderText("例如: *班, *B班")
        selection_layout.addWidget(self.class_pattern_input, 2, 1)

        layout.addLayout(selection_layout)

        # 检测配置
        detect_layout = QVBoxLayout()
        detect_label = QLabel("检测配置:")

        self.threshold_label = QLabel(f"相似度阈值: 60%")
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(60)
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)

        self.cross_class_cb = QCheckBox("启用跨班级检测")
        self.cross_class_cb.setChecked(True)

        detect_layout.addWidget(detect_label)
        detect_layout.addWidget(self.threshold_label)
        detect_layout.addWidget(self.threshold_slider)
        detect_layout.addWidget(self.cross_class_cb)

        layout.addLayout(detect_layout)

        # 控制按钮
        control_layout = QVBoxLayout()
        control_label = QLabel("操作:")

        self.discover_btn = QPushButton("🔍 发现班级")
        self.discover_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)

        self.start_btn = QPushButton("🚀 开始检测")
        self.start_btn.setEnabled(False)
        self.start_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        control_layout.addWidget(control_label)
        control_layout.addWidget(self.discover_btn)
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        parent_layout.addWidget(group)

    def _create_left_section(self) -> QWidget:
        """创建左侧区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 班级列表
        class_group = QGroupBox("发现的班级")
        class_layout = QVBoxLayout()

        self.class_table = QTableWidget()
        self.class_table.setColumnCount(5)
        self.class_table.setHorizontalHeaderLabels([
            "班级ID", "班级名称", "学生数", "提交数", "状态"
        ])

        self.class_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.class_table.horizontalHeader().setStretchLastSection(True)
        self.class_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.class_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                gridline-color: #e9ecef;
                selection-background-color: #3498db;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: none;
                border-bottom: 2px solid #dee2e6;
                padding: 10px;
                font-weight: bold;
                color: #495057;
            }
        """)

        self.class_table.itemClicked.connect(self._on_class_selected)

        class_layout.addWidget(self.class_table)
        class_group.setLayout(class_layout)

        layout.addWidget(class_group)

        # 进度区域
        progress_group = QGroupBox("检测进度")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e9ecef;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 3px;
            }
        """)

        self.detection_status_label = QLabel("等待开始...")
        self.detection_status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                padding: 5px;
            }
        """)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.detection_status_label)
        progress_group.setLayout(progress_layout)

        layout.addWidget(progress_group)

        return widget

    def _create_right_section(self) -> QWidget:
        """创建右侧区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid white;
            }
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # 统计概览标签页
        stats_tab = self._create_stats_tab()
        tab_widget.addTab(stats_tab, "📊 统计概览")

        # 跨班级对比标签页
        comparison_tab = self._create_comparison_tab()
        tab_widget.addTab(comparison_tab, "🔗 跨班级对比")

        # 详细结果标签页
        results_tab = self._create_results_tab()
        tab_widget.addTab(results_tab, "📋 详细结果")

        layout.addWidget(tab_widget)

        return widget

    def _create_stats_tab(self) -> QWidget:
        """创建统计概览标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 总体统计
        overall_group = QGroupBox("总体统计")
        overall_layout = QGridLayout()

        self.total_classes_label = QLabel("班级数: 0")
        self.total_students_label = QLabel("学生总数: 0")
        self.total_submissions_label = QLabel("提交总数: 0")
        self.avg_similarity_label = QLabel("平均相似度: --")

        for i, label in enumerate([
            self.total_classes_label,
            self.total_students_label,
            self.total_submissions_label,
            self.avg_similarity_label
        ]):
            label.setStyleSheet("""
                QLabel {
                    padding: 15px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                    color: #495057;
                }
            """)
            overall_layout.addWidget(label, 0, i)

        overall_group.setLayout(overall_layout)
        layout.addWidget(overall_group)

        # 班级详情统计
        class_stats_group = QGroupBox("班级统计")
        class_stats_layout = QVBoxLayout()

        self.class_stats_label = QLabel("等待检测结果...")
        self.class_stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.class_stats_label.setStyleSheet("""
            QLabel {
                padding: 30px;
                background-color: #f8f9fa;
                border-radius: 8px;
                color: #6c757d;
            }
        """)

        class_stats_layout.addWidget(self.class_stats_label)
        class_stats_group.setLayout(class_stats_layout)

        layout.addWidget(class_stats_group, 1)

        return widget

    def _create_comparison_tab(self) -> QWidget:
        """创建跨班级对比标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 对比表格
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(4)
        self.comparison_table.setHorizontalHeaderLabels([
            "班级对比", "平均相似度", "可疑对数", "跨班级对数"
        ])

        self.comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        self.comparison_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.comparison_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                gridline-color: #e9ecef;
                selection-background-color: #3498db;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: none;
                border-bottom: 2px solid #dee2e6;
                padding: 10px;
                font-weight: bold;
                color: #495057;
            }
        """)

        self.comparison_label = QLabel("等待检测结果...")
        self.comparison_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comparison_label.setStyleSheet("""
            QLabel {
                padding: 30px;
                background-color: #f8f9fa;
                border-radius: 8px;
                color: #6c757d;
            }
        """)

        # 使用堆叠布局切换显示
        self.comparison_stack = QStackedWidget()
        self.comparison_stack.addWidget(self.comparison_label)
        self.comparison_stack.addWidget(self.comparison_table)
        self.comparison_stack.setCurrentIndex(0)

        layout.addWidget(self.comparison_stack)

        return widget

    def _create_results_tab(self) -> QWidget:
        """创建详细结果标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 结果详情
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setPlaceholderText("检测结果将在这里显示...")
        self.results_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
            }
        """)

        layout.addWidget(self.results_text)

        # 报告生成按钮
        report_layout = QHBoxLayout()
        report_layout.addStretch()

        self.generate_report_btn = QPushButton("📄 生成报告")
        self.generate_report_btn.setEnabled(False)
        self.generate_report_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        report_layout.addWidget(self.generate_report_btn)
        layout.addLayout(report_layout)

        return widget

    def _connect_signals(self):
        """连接信号"""
        try:
            if hasattr(self, 'discover_btn') and self.discover_btn:
                self.discover_btn.clicked.connect(self._on_discover_classes_safe)
            if hasattr(self, 'start_btn') and self.start_btn:
                self.start_btn.clicked.connect(self._on_start_detection)
            if hasattr(self, 'stop_btn') and self.stop_btn:
                self.stop_btn.clicked.connect(self._on_stop_detection)
            if hasattr(self, 'generate_report_btn') and self.generate_report_btn:
                self.generate_report_btn.clicked.connect(self._on_generate_report)

            if self.multi_class_service:
                self.multi_class_service.detection_progress.connect(self._on_progress_updated)
                self.multi_class_service.detection_completed.connect(self._on_detection_completed)
                self.multi_class_service.detection_failed.connect(self._on_detection_failed)
                self.multi_class_service.report_generated.connect(self._on_report_generated)
        except Exception as e:
            print(f"[ERROR] 连接信号失败: {e}", file=sys.stderr)

    def _on_discover_classes_safe(self):
        """安全版本：捕获所有异常防止闪退"""
        try:
            print("[DEBUG] _on_discover_classes_safe 开始", file=sys.stderr)
            print(f"[DEBUG] self.base_path = {self.base_path}", file=sys.stderr)
            print(f"[DEBUG] _service_available = {getattr(self, '_service_available', False)}", file=sys.stderr)
            print(f"[DEBUG] multi_class_service = {self.multi_class_service}", file=sys.stderr)
            self._on_discover_classes()
            print("[DEBUG] _on_discover_classes 完成", file=sys.stderr)
        except Exception as e:
            import traceback
            error_msg = f"发现班级时发生错误:\n{str(e)}\n\n详细信息:\n{traceback.format_exc()}"
            print(f"[ERROR] {error_msg}", file=sys.stderr)
            from PyQt6.QtWidgets import QMessageBox
            try:
                QMessageBox.critical(
                    self,
                    "发现班级失败",
                    error_msg
                )
            except:
                pass
            self.status_changed.emit(f"发现班级失败: {str(e)}")

    def _on_select_base_path(self):
        """选择基础路径"""
        # 创建临时config用于路径检测
        from app.config.settings import ConfigManager
        from app.ui.file_dialog_utils import DialogStartDir
        config_manager = ConfigManager()

        # 创建默认配置（会自动检测安装目录）
        default_config = config_manager.create_default_config()

        # 优先使用教学目录作为起始路径
        install_dir = DialogStartDir._get_install_dir()
        start_dir = None
        if install_dir:
            # 尝试多种可能的教学目录位置
            possible_dirs = [
                install_dir / 'docs' / 'teaching',      # 开发环境
                install_dir / 'teaching',               # 直接在安装目录下
                install_dir / 'data' / 'teaching',      # 打包版本
                install_dir / 'data' / 'teaching_demo', # 旧名称兼容
            ]
            for dir_path in possible_dirs:
                if dir_path.exists():
                    start_dir = str(dir_path)
                    break
        elif default_config and default_config.experiment_dir:
            start_dir = str(default_config.experiment_dir)

        # 如果找到起始路径，使用它
        if start_dir:
            # 临时设置起始路径
            DialogStartDir._last_dirs['submission'] = start_dir

        dir_path = get_existing_directory(
            self,
            "选择教学基础目录（应包含学期目录，如 2026-春季）",
            'submission',
            default_config  # 使用默认配置来获取起始路径
        )

        if dir_path:
            # 确保路径是绝对路径
            path_obj = Path(dir_path)
            if not path_obj.is_absolute():
                # 如果是相对路径，尝试从安装目录解析
                install_dir = DialogStartDir._get_install_dir()
                if install_dir:
                    path_obj = install_dir / path_obj
                else:
                    # 如果无法获取安装目录，使用当前工作目录
                    path_obj = Path.cwd() / path_obj

            # 验证路径是否存在
            if path_obj.exists():
                self.base_path_label.setText(str(path_obj))
                self.base_path = path_obj
            else:
                self.base_path_label.setText(f"路径不存在: {dir_path}")
                self.status_changed.emit(f"选择的路径不存在: {dir_path}")

    def _on_threshold_changed(self, value):
        """阈值改变"""
        self.threshold_label.setText(f"相似度阈值: {value}%")

    def _on_discover_classes(self):
        """发现班级"""
        print("[DEBUG] _on_discover_classes 开始执行", file=sys.stderr)

        # 检查服务是否可用
        if not getattr(self, '_service_available', False) or self.multi_class_service is None:
            print("[ERROR] MultiClassService 不可用", file=sys.stderr)
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "功能不可用",
                "多班级检测服务不可用，可能是缺少必要的模块。\n\n请确保程序完整安装。"
            )
            return

        # 检查 base_path 是否已设置
        if self.base_path is None:
            print("[ERROR] base_path 未设置", file=sys.stderr)
            self.status_changed.emit("请先选择基础路径")
            return

        # 验证路径是否存在
        if not self.base_path.exists():
            print(f"[ERROR] 基础路径不存在: {self.base_path}", file=sys.stderr)
            self.status_changed.emit(f"基础路径不存在: {self.base_path}")
            return

        print(f"[INFO] 使用基础路径: {self.base_path}", file=sys.stderr)

        # 获取配置
        try:
            semester = self.semester_combo.currentData()
            if not semester:
                semester = "2026-春季"

            experiment = self.experiment_combo.currentData()
            if not experiment:
                experiment = "07-car-gear"

            class_pattern = self.class_pattern_input.text() or "*班"
            print(f"[INFO] 配置: semester={semester}, experiment={experiment}, pattern={class_pattern}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] 获取配置失败: {e}", file=sys.stderr)
            self.status_changed.emit(f"获取配置失败: {str(e)}")
            return

        # 验证 class_pattern 不包含路径遍历攻击
        if not class_pattern:
            class_pattern = "*班"
        else:
            # 检查是否包含路径遍历字符
            if '..' in class_pattern or '/' in class_pattern or '\\' in class_pattern:
                print("[ERROR] 班级模式包含非法字符", file=sys.stderr)
                self.status_changed.emit("班级模式包含非法字符")
                return
            # 限制模式长度
            if len(class_pattern) > 50:
                print("[ERROR] 班级模式过长", file=sys.stderr)
                self.status_changed.emit("班级模式过长")
                return

        try:
            print("[INFO] 开始调用 discover_classes", file=sys.stderr)
            # 调用服务发现班级
            classes = self.multi_class_service.discover_classes(
                base_dir=self.base_path,
                semester=semester,
                experiment=experiment,
                class_pattern=class_pattern
            )
            print(f"[INFO] discover_classes 返回类型: {type(classes)}", file=sys.stderr)
            print(f"[INFO] discover_classes 返回: {len(classes) if classes else 0} 个班级", file=sys.stderr)

            self.discovered_classes = classes if classes else []
            print(f"[DEBUG] 赋值后 discovered_classes 类型: {type(self.discovered_classes)}", file=sys.stderr)
            print(f"[DEBUG] 赋值后 discovered_classes 值: {self.discovered_classes}", file=sys.stderr)

            print("[DEBUG] 调用 _display_discovered_classes", file=sys.stderr)
            self._display_discovered_classes(self.discovered_classes)
            print("[DEBUG] _display_discovered_classes 完成", file=sys.stderr)

            # 启用开始按钮
            print("[DEBUG] 检查 discovered_classes", file=sys.stderr)
            if self.discovered_classes:
                print(f"[DEBUG] discovered_classes 非空，调用 start_btn.setEnabled(True)", file=sys.stderr)
                self.start_btn.setEnabled(True)
                self.status_changed.emit(f"发现 {len(self.discovered_classes)} 个班级")
                print(f"[SUCCESS] 发现 {len(self.discovered_classes)} 个班级", file=sys.stderr)
            else:
                print("[DEBUG] discovered_classes 为空，不启用开始按钮", file=sys.stderr)
                self.status_changed.emit("未发现任何班级，请检查路径配置")
                print("[WARNING] 未发现任何班级", file=sys.stderr)

        except ImportError as e:
            import traceback
            print(f"[ERROR] 模块导入失败: {e}\n{traceback.format_exc()}", file=sys.stderr)
            from PyQt6.QtWidgets import QMessageBox
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "模块导入失败",
                f"缺少必要的模块:\n{str(e)}\n\n请确保程序完整安装。"
            )
            self.status_changed.emit(f"模块导入失败: {str(e)}")

        except Exception as e:
            import traceback
            print(f"[ERROR] 发现班级失败: {e}\n{traceback.format_exc()}", file=sys.stderr)
            from PyQt6.QtWidgets import QMessageBox
            error_details = traceback.format_exc()
            QMessageBox.critical(
                self,
                "发现班级失败",
                f"错误信息:\n{str(e)}\n\n详细信息:\n{error_details}"
            )
            self.status_changed.emit(f"发现班级失败: {str(e)}")

    def _on_start_detection(self):
        """开始检测"""
        try:
            print("[DEBUG] _on_start_detection 开始", file=sys.stderr)
            if not self.discovered_classes:
                print("[WARNING] discovered_classes 为空，无法开始检测", file=sys.stderr)
                return

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.discover_btn.setEnabled(False)

            # 创建配置
            project_name = f"{self.semester_combo.currentText()} - {self.experiment_combo.currentText()}"
            threshold = self.threshold_slider.value()
            enable_cross_class = self.cross_class_cb.isChecked()

            print(f"[DEBUG] 创建配置: project_name={project_name}, threshold={threshold}", file=sys.stderr)

            config = self.multi_class_service.create_config(
                project_name=project_name,
                class_configs=self.discovered_classes,
                threshold=threshold,
                enable_cross_class=enable_cross_class
            )

            # 设置班级信息
            from app.models.domain import ClassConfig, ExperimentType
            config.classes = [
                ClassConfig(
                    class_id=c.get('class_id', ''),
                    class_name=c.get('class_name', ''),
                    experiment_dir=Path(c.get('experiment_dir', '')),
                    experiment_type=ExperimentType.CAR_GEAR,
                    submissions_dir=Path(c['submissions_dir']) if c.get('submissions_dir') else None
                )
                for c in self.discovered_classes
                if c.get('class_id') and c.get('class_name') and c.get('experiment_dir')
            ]

            print(f"[DEBUG] 配置了 {len(config.classes)} 个班级", file=sys.stderr)
            self.current_config = config

            # 启动检测
            print("[DEBUG] 调用 start_detection", file=sys.stderr)
            self.multi_class_service.start_detection(config)
            print("[DEBUG] start_detection 调用完成", file=sys.stderr)

        except Exception as e:
            import traceback
            print(f"[ERROR] 开始检测失败: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            self._reset_ui()
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "检测失败",
                f"开始检测时发生错误:\n\n{str(e)}\n\n详细信息请查看控制台输出"
            )

    def _on_stop_detection(self):
        """停止检测"""
        self.multi_class_service.stop_detection()
        self._reset_ui()

    def _on_class_selected(self, item):
        """班级选中"""
        row = item.row()
        class_id = self.class_table.item(row, 0).text()
        self.selected_class_id = class_id
        self.class_selected.emit(class_id)

    def _on_progress_updated(self, progress: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.detection_status_label.setText(message)

    def _on_detection_completed(self, results):
        """检测完成"""
        self._reset_ui()
        self._display_results(results)
        self.generate_report_btn.setEnabled(True)
        self.status_changed.emit("多班级检测完成")

    def _on_detection_failed(self, error: str):
        """检测失败"""
        self._reset_ui()
        self.detection_status_label.setText(f"检测失败: {error}")
        self.status_changed.emit(f"检测失败: {error}")

    def _on_generate_report(self):
        """生成报告"""
        if not self.current_config or not self.multi_class_service.get_results():
            return

        # 选择输出目录
        output_dir = get_existing_directory(
            self,
            "选择报告输出目录",
            'output',
            self.current_config
        )

        if output_dir:
            try:
                report_paths = self.multi_class_service.generate_reports(
                    output_dir=Path(output_dir),
                    formats=['excel', 'json']
                )
                self.status_changed.emit(f"报告已生成: {len(report_paths)} 个文件")
            except Exception as e:
                self.status_changed.emit(f"生成报告失败: {str(e)}")

    def _on_report_generated(self, report_paths):
        """报告生成完成"""
        self.status_changed.emit(f"报告已生成: {report_paths}")

    def _display_discovered_classes(self, classes: List[Dict]):
        """显示发现的班级"""
        if classes is None:
            classes = []

        # 确保 class_table 存在
        if not hasattr(self, 'class_table') or self.class_table is None:
            return

        try:
            self.class_table.setRowCount(0)

            for i, class_info in enumerate(classes):
                if not isinstance(class_info, dict):
                    continue

                self.class_table.insertRow(i)

                class_id = class_info.get('class_id', '')
                class_name = class_info.get('class_name', '')

                self.class_table.setItem(i, 0, QTableWidgetItem(str(class_id)))
                self.class_table.setItem(i, 1, QTableWidgetItem(str(class_name)))
                self.class_table.setItem(i, 2, QTableWidgetItem("0"))
                self.class_table.setItem(i, 3, QTableWidgetItem("0"))

                status_item = QTableWidgetItem("📋 待检测")
                status_item.setForeground(QColor(0x6c757d))
                self.class_table.setItem(i, 4, status_item)
        except Exception as e:
            import sys
            print(f"显示班级列表失败: {str(e)}", file=sys.stderr)

    def _display_results(self, results):
        """显示检测结果"""
        if results is None:
            return

        # 更新班级表格状态
        try:
            for row in range(self.class_table.rowCount()):
                class_id_item = self.class_table.item(row, 0)
                status_item = self.class_table.item(row, 4)

                if class_id_item and status_item:
                    # class_id = class_id_item.text()  # 暂未使用
                    status_item.setText("✅ 已检测")
                    status_item.setForeground(QColor(0x28a745))
        except Exception as e:
            import sys
            print(f"更新班级表格状态失败: {str(e)}", file=sys.stderr)

        # 显示统计信息
        self._display_statistics(results)

        # 显示对比信息
        self._display_comparisons(results)

        # 显示详细结果
        self._display_detailed_results(results)

    def _display_statistics(self, results):
        """显示统计信息"""
        if results is None:
            return

        try:
            # 总体统计
            if hasattr(results, 'class_results') and results.class_results:
                # class_results 是 Dict[str, ClassDetectionResult]
                class_result_dict = results.class_results
                class_result_values = class_result_dict.values() if isinstance(class_result_dict, dict) else class_result_dict

                total_students = sum(r.student_count for r in class_result_values)
                total_suspicious = sum(r.suspicious_pairs for r in class_result_values)

                self.total_classes_label.setText(f"班级数: {len(class_result_dict)}")
                self.total_students_label.setText(f"学生总数: {total_students}")
                self.total_submissions_label.setText(f"可疑对数: {total_suspicious}")

                # 班级统计
                stats_html = "<div style='font-family: monospace;'>"
                stats_html += "<h3>班级统计详情</h3>"
                stats_html += "<table style='width: 100%; border-collapse: collapse;'>"

                for class_result in class_result_values:
                    class_name = class_result.class_name
                    student_count = class_result.student_count
                    suspicious_count = class_result.suspicious_pairs

                    stats_html += f"""
                    <tr style='border-bottom: 1px solid #dee2e6;'>
                        <td style='padding: 8px;'>{class_name}</td>
                        <td style='padding: 8px;'>{student_count} 人</td>
                        <td style='padding: 8px;'>{suspicious_count} 对可疑</td>
                        <td style='padding: 8px; color: {'#dc3545' if suspicious_count > 0 else '#28a745'};'>{'可疑' if suspicious_count > 0 else '正常'}</td>
                    </tr>
                    """

                stats_html += "</table></div>"
                self.class_stats_label.setText(stats_html)
        except Exception as e:
            import sys
            print(f"显示统计信息失败: {str(e)}", file=sys.stderr)

    def _display_comparisons(self, results):
        """显示跨班级对比"""
        if results is None:
            return

        try:
            self.comparison_stack.setCurrentIndex(1)
        except Exception as e:
            import sys
            print(f"切换对比页面失败: {str(e)}", file=sys.stderr)
            return

        # 如果有跨班级对比结果（使用 class_comparisons，这是一个 dict 列表）
        if hasattr(results, 'class_comparisons') and results.class_comparisons:
            try:
                self.comparison_table.setRowCount(0)
            except Exception as e:
                import sys
                print(f"清空对比表格失败: {str(e)}", file=sys.stderr)
                return

            for i, comparison in enumerate(results.class_comparisons):
                if not comparison:
                    continue

                self.comparison_table.insertRow(i)

                try:
                    # class_comparisons 是 dict 列表，使用 get 访问
                    class_name_1 = comparison.get('class_name_1', '')
                    class_name_2 = comparison.get('class_name_2', '')
                    comparison_name = f"{class_name_1} vs {class_name_2}"
                    self.comparison_table.setItem(i, 0, QTableWidgetItem(comparison_name))

                    # 平均相似度
                    avg_sim = comparison.get('avg_similarity', 0)
                    sim_item = QTableWidgetItem(f"{avg_sim:.1f}%")
                    if avg_sim > 70:
                        sim_item.setForeground(QColor(0xdc3545))
                    elif avg_sim > 50:
                        sim_item.setForeground(QColor(0xffc107))
                    self.comparison_table.setItem(i, 1, sim_item)

                    # 可疑对数
                    suspicious_pairs = comparison.get('suspicious_pairs', 0)
                    self.comparison_table.setItem(i, 2, QTableWidgetItem(str(suspicious_pairs)))

                    # 跨班级对数
                    cross_class_pairs = comparison.get('cross_class_pairs', 0)
                    self.comparison_table.setItem(i, 3, QTableWidgetItem(str(cross_class_pairs)))
                except Exception as e:
                    # 如果单个对比项处理失败，跳过该项
                    import sys
                    print(f"处理对比项失败: {str(e)}", file=sys.stderr)
                    continue

    def _display_detailed_results(self, results):
        """显示详细结果"""
        if results is None:
            return

        try:
            self.results_text.clear()
        except Exception as e:
            import sys
            print(f"清空结果文本失败: {str(e)}", file=sys.stderr)
            return

        # 生成结果摘要
        detection_time = getattr(results, 'timestamp', '未知')
        class_results = getattr(results, 'class_results', {})
        # class_results 是 Dict[str, ClassDetectionResult]，需要获取值
        class_result_values = class_results.values() if isinstance(class_results, dict) else class_results
        summary = f"""
====================================
多班级查重检测结果摘要
====================================

检测时间: {detection_time}
班级数量: {len(class_result_values)}

"""

        for class_result in class_result_values:
            # ClassDetectionResult 是 dataclass，直接访问属性
            class_name = class_result.class_name
            student_count = class_result.student_count
            suspicious_count = class_result.suspicious_pairs

            summary += f"""
班级: {class_name}
- 学生数: {student_count}
- 可疑对数: {suspicious_count}

"""

        # MultiClassDetectionResult 使用 class_comparisons (dict 列表)
        if hasattr(results, 'class_comparisons') and results.class_comparisons:
            summary += "\n跨班级对比:\n"
            for comp in results.class_comparisons:
                summary += f"- {comp.get('class_name_1', '')} vs {comp.get('class_name_2', '')}: {comp.get('avg_similarity', 0):.1f}% 平均相似度\n"

        self.results_text.setText(summary)

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(len(self.discovered_classes) > 0 if self.discovered_classes else False)
        self.stop_btn.setEnabled(False)
        self.discover_btn.setEnabled(True)

    def set_config(self, config: MultiClassProjectConfig):
        """设置配置"""
        self.current_config = config

        if config.classes:
            self.discovered_classes = [c.to_dict() for c in config.classes]
            self._display_discovered_classes(self.discovered_classes)
            self.start_btn.setEnabled(True)
