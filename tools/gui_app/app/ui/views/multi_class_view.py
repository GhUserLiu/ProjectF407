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
    QScrollArea, QSpinBox, QTabWidget, QLineEdit, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QBrush

# 添加项目根目录到Python路径
project_root = Path(__file__).parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.models.domain import MultiClassProjectConfig, ClassConfig, CrossClassComparison
from app.core.multi_class_service import MultiClassService


class MultiClassView(QWidget):
    """多班级处理视图"""

    # 信号
    status_changed = pyqtSignal(str)
    class_selected = pyqtSignal(str)  # 班级ID

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[MultiClassProjectConfig] = None
        self.multi_class_service = MultiClassService()
        self.discovered_classes: List[Dict] = []
        self.selected_class_id: Optional[str] = None

        self._init_ui()
        self._connect_signals()

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
        self.discover_btn.clicked.connect(self._on_discover_classes)
        self.start_btn.clicked.connect(self._on_start_detection)
        self.stop_btn.clicked.connect(self._on_stop_detection)
        self.generate_report_btn.clicked.connect(self._on_generate_report)

        self.multi_class_service.detection_progress.connect(self._on_progress_updated)
        self.multi_class_service.detection_completed.connect(self._on_detection_completed)
        self.multi_class_service.detection_failed.connect(self._on_detection_failed)
        self.multi_class_service.report_generated.connect(self._on_report_generated)

    def _on_select_base_path(self):
        """选择基础路径"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择教学基础目录",
            str(Path.cwd())
        )

        if dir_path:
            self.base_path_label.setText(dir_path)
            self.base_path = Path(dir_path)

    def _on_threshold_changed(self, value):
        """阈值改变"""
        self.threshold_label.setText(f"相似度阈值: {value}%")

    def _on_discover_classes(self):
        """发现班级"""
        if not hasattr(self, 'base_path'):
            self.status_changed.emit("请先选择基础路径")
            return

        # 获取配置
        semester = self.semester_combo.currentData()
        experiment = self.experiment_combo.currentData()
        class_pattern = self.class_pattern_input.text() or "*班"

        try:
            # 调用服务发现班级
            classes = self.multi_class_service.discover_classes(
                base_dir=self.base_path,
                semester=semester,
                experiment=experiment,
                class_pattern=class_pattern
            )

            self.discovered_classes = classes
            self._display_discovered_classes(classes)

            # 启用开始按钮
            if classes:
                self.start_btn.setEnabled(True)
                self.status_changed.emit(f"发现 {len(classes)} 个班级")
            else:
                self.status_changed.emit("未发现任何班级")

        except Exception as e:
            self.status_changed.emit(f"发现班级失败: {str(e)}")

    def _on_start_detection(self):
        """开始检测"""
        if not self.discovered_classes:
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.discover_btn.setEnabled(False)

        # 创建配置
        project_name = f"{self.semester_combo.currentText()} - {self.experiment_combo.currentText()}"
        threshold = self.threshold_slider.value()
        enable_cross_class = self.cross_class_cb.isChecked()

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
                class_id=c['class_id'],
                class_name=c['class_name'],
                experiment_dir=Path(c['experiment_dir']),
                experiment_type=ExperimentType.CAR_GEAR,
                submissions_dir=Path(c['submissions_dir']) if c.get('submissions_dir') else None
            )
            for c in self.discovered_classes
        ]

        self.current_config = config

        # 启动检测
        self.multi_class_service.start_detection(config)

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
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "选择报告输出目录",
            str(self.current_config.output_dir or Path.cwd())
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
        self.class_table.setRowCount(0)

        for i, class_info in enumerate(classes):
            self.class_table.insertRow(i)

            self.class_table.setItem(i, 0, QTableWidgetItem(class_info.get('class_id', '')))
            self.class_table.setItem(i, 1, QTableWidgetItem(class_info.get('class_name', '')))
            self.class_table.setItem(i, 2, QTableWidgetItem("0"))
            self.class_table.setItem(i, 3, QTableWidgetItem("0"))

            status_item = QTableWidgetItem("📋 待检测")
            status_item.setForeground(QColor(0x6c757d))
            self.class_table.setItem(i, 4, status_item)

    def _display_results(self, results):
        """显示检测结果"""
        # 更新班级表格状态
        for row in range(self.class_table.rowCount()):
            class_id = self.class_table.item(row, 0).text()
            status_item = self.class_table.item(row, 4)
            status_item.setText("✅ 已检测")
            status_item.setForeground(QColor(0x28a745))

        # 显示统计信息
        self._display_statistics(results)

        # 显示对比信息
        self._display_comparisons(results)

        # 显示详细结果
        self._display_detailed_results(results)

    def _display_statistics(self, results):
        """显示统计信息"""
        # 总体统计
        if hasattr(results, 'class_results'):
            total_students = sum(len(r.get('students', [])) for r in results.class_results)
            total_submissions = sum(r.get('submission_count', 0) for r in results.class_results)

            self.total_classes_label.setText(f"班级数: {len(results.class_results)}")
            self.total_students_label.setText(f"学生总数: {total_students}")
            self.total_submissions_label.setText(f"提交总数: {total_submissions}")

            # 班级统计
            stats_html = "<div style='font-family: monospace;'>"
            stats_html += "<h3>班级统计详情</h3>"
            stats_html += "<table style='width: 100%; border-collapse: collapse;'>"

            for class_result in results.class_results:
                class_name = class_result.get('class_name', '未知')
                student_count = len(class_result.get('students', []))
                submission_count = class_result.get('submission_count', 0)
                suspicious_count = class_result.get('suspicious_count', 0)

                stats_html += f"""
                <tr style='border-bottom: 1px solid #dee2e6;'>
                    <td style='padding: 8px;'>{class_name}</td>
                    <td style='padding: 8px;'>{student_count} 人</td>
                    <td style='padding: 8px;'>{submission_count} 份提交</td>
                    <td style='padding: 8px; color: {'#dc3545' if suspicious_count > 0 else '#28a745'};'>{suspicious_count} 可疑</td>
                </tr>
                """

            stats_html += "</table></div>"
            self.class_stats_label.setText(stats_html)

    def _display_comparisons(self, results):
        """显示跨班级对比"""
        self.comparison_stack.setCurrentIndex(1)

        # 如果有跨班级对比结果
        if hasattr(results, 'cross_class_comparisons'):
            self.comparison_table.setRowCount(0)

            for i, comparison in enumerate(results.cross_class_comparisons):
                self.comparison_table.insertRow(i)

                # 班级对比名称
                comparison_name = f"{comparison.class_name_1} vs {comparison.class_name_2}"
                self.comparison_table.setItem(i, 0, QTableWidgetItem(comparison_name))

                # 平均相似度
                avg_sim = comparison.avg_similarity
                sim_item = QTableWidgetItem(f"{avg_sim:.1f}%")
                if avg_sim > 70:
                    sim_item.setForeground(QColor(0xdc3545))
                elif avg_sim > 50:
                    sim_item.setForeground(QColor(0xffc107))
                self.comparison_table.setItem(i, 1, sim_item)

                # 可疑对数
                self.comparison_table.setItem(i, 2, QTableWidgetItem(str(comparison.suspicious_pairs)))

                # 跨班级对数
                self.comparison_table.setItem(i, 3, QTableWidgetItem(str(comparison.cross_class_pairs)))

    def _display_detailed_results(self, results):
        """显示详细结果"""
        self.results_text.clear()

        # 生成结果摘要
        summary = f"""
====================================
多班级查重检测结果摘要
====================================

检测时间: {getattr(results, 'detection_time', '未知')}
班级数量: {len(getattr(results, 'class_results', []))}

"""

        for class_result in getattr(results, 'class_results', []):
            class_name = class_result.get('class_name', '未知')
            students = class_result.get('students', [])
            suspicious_count = class_result.get('suspicious_count', 0)

            summary += f"""
班级: {class_name}
- 学生数: {len(students)}
- 可疑对数: {suspicious_count}

"""

        if hasattr(results, 'cross_class_comparisons'):
            summary += "\n跨班级对比:\n"
            for comp in results.cross_class_comparisons:
                summary += f"- {comp.class_name_1} vs {comp.class_name_2}: {comp.avg_similarity:.1f}% 平均相似度\n"

        self.results_text.setText(summary)

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(self.discovered_classes and len(self.discovered_classes) > 0)
        self.stop_btn.setEnabled(False)
        self.discover_btn.setEnabled(True)

    def set_config(self, config: MultiClassProjectConfig):
        """设置配置"""
        self.current_config = config

        if config.classes:
            self.discovered_classes = [c.to_dict() for c in config.classes]
            self._display_discovered_classes(self.discovered_classes)
            self.start_btn.setEnabled(True)


# 导入QStackedWidget
from PyQt6.QtWidgets import QStackedWidget
