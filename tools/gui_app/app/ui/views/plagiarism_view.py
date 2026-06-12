"""
查重检测视图

提供查重检测的用户界面
"""

from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QCheckBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QSplitter, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from app.models.domain import ProjectConfig, PlagiarismPair, SimilarityLevel
from app.core.plagiarism import PlagiarismService
from app.ui.file_dialog_utils import get_existing_directory


class PlagiarismView(QWidget):
    """查重检测视图"""

    # 信号
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None
        self.plagiarism_service = PlagiarismService(self)

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
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 进度区域
        progress_widget = self._create_progress_section()
        splitter.addWidget(progress_widget)

        # 结果表格区域
        result_widget = self._create_result_section()
        splitter.addWidget(result_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([150, 400])

        layout.addWidget(splitter)

    def _create_config_section(self, parent_layout):
        """创建配置区域"""
        group = QGroupBox("检测配置")
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

        # 文件选择
        file_layout = QVBoxLayout()
        file_label = QLabel("提交目录:")
        self.file_label = QLabel("未选择")
        self.file_label.setStyleSheet("color: #6c757d; padding: 5px;")
        self.file_label.setFrameStyle(QFrame.Shape.Panel | QFrame.Shadow.Sunken)

        select_btn = QPushButton("📁 选择目录")
        select_btn.clicked.connect(self._on_select_directory)
        select_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(select_btn)
        file_layout.addStretch()

        layout.addLayout(file_layout)

        # 阈值配置
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("检测阈值:")

        self.suspicious_spin = QDoubleSpinBox()
        self.suspicious_spin.setRange(0, 100)
        self.suspicious_spin.setValue(60)
        self.suspicious_spin.setSuffix("%")
        self.suspicious_spin.setToolTip("可疑阈值")

        self.plagiarism_spin = QDoubleSpinBox()
        self.plagiarism_spin.setRange(0, 100)
        self.plagiarism_spin.setValue(85)
        self.plagiarism_spin.setSuffix("%")
        self.plagiarism_spin.setToolTip("抄袭阈值")

        threshold_row = QHBoxLayout()
        threshold_row.addWidget(QLabel("可疑:"))
        threshold_row.addWidget(self.suspicious_spin)
        threshold_row.addWidget(QLabel("抄袭:"))
        threshold_row.addWidget(self.plagiarism_spin)

        threshold_layout.addWidget(threshold_label)
        threshold_layout.addLayout(threshold_row)
        threshold_layout.addStretch()

        layout.addLayout(threshold_layout)

        # 检测选项
        options_layout = QVBoxLayout()
        options_label = QLabel("检测选项:")

        self.filter_template_cb = QCheckBox("启用模板过滤")
        self.filter_template_cb.setChecked(True)
        self.semantic_cb = QCheckBox("启用语义检测")
        self.semantic_cb.setChecked(True)
        self.code_obfuscation_cb = QCheckBox("启用代码混淆检测")

        options_layout.addWidget(options_label)
        options_layout.addWidget(self.filter_template_cb)
        options_layout.addWidget(self.semantic_cb)
        options_layout.addWidget(self.code_obfuscation_cb)
        options_layout.addStretch()

        layout.addLayout(options_layout)

        # 控制按钮
        control_layout = QVBoxLayout()
        control_label = QLabel("控制:")

        self.start_btn = QPushButton("🚀 开始检测")
        self.start_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #ffc107;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)

        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
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
        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        parent_layout.addWidget(group)

    def _create_progress_section(self) -> QWidget:
        """创建进度区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e9ecef;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                padding: 5px;
            }
        """)
        layout.addWidget(self.status_label)

        # 统计信息
        stats_group = QGroupBox("实时统计")
        stats_layout = QHBoxLayout()

        self.total_label = QLabel("检测人数: 0")
        self.suspicious_label = QLabel("可疑对数: 0")
        self.plagiarism_label = QLabel("涉嫌人数: 0")
        self.max_label = QLabel("最高相似度: 0%")

        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.suspicious_label)
        stats_layout.addWidget(self.plagiarism_label)
        stats_layout.addWidget(self.max_label)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 日志区域
        log_group = QGroupBox("检测日志")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        return widget

    def _create_result_section(self) -> QWidget:
        """创建结果区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(7)
        self.result_table.setHorizontalHeaderLabels([
            "学号", "姓名1", "学号", "姓名2", "相似度", "类型", "状态"
        ])

        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setStyleSheet("""
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

        layout.addWidget(self.result_table)

        # 操作按钮
        action_layout = QHBoxLayout()

        self.export_btn = QPushButton("📊 导出报告")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_report)

        self.clear_btn = QPushButton("🗑️ 清空结果")
        self.clear_btn.clicked.connect(self._on_clear_results)

        action_layout.addStretch()
        action_layout.addWidget(self.export_btn)
        action_layout.addWidget(self.clear_btn)

        layout.addLayout(action_layout)

        return widget

    def _connect_signals(self):
        """连接信号"""
        self.start_btn.clicked.connect(self._on_start_detection)
        self.pause_btn.clicked.connect(self._on_pause_detection)
        self.stop_btn.clicked.connect(self._on_stop_detection)

        self.plagiarism_service.progress_updated.connect(self._on_progress_updated)
        self.plagiarism_service.detection_finished.connect(self._on_detection_finished)
        self.plagiarism_service.detection_failed.connect(self._on_detection_failed)
        self.plagiarism_service.log_message.connect(self._on_log_message)

    def _on_select_directory(self):
        """选择目录"""
        directory = get_existing_directory(
            self,
            "选择提交目录",
            'submission',
            self.current_config
        )
        if directory:
            self.file_label.setText(directory)
            self.file_path = directory

    def _on_start_detection(self):
        """开始检测"""
        if not hasattr(self, 'file_path') or not self.file_path:
            self._show_error("请先选择提交目录")
            return

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.result_table.setRowCount(0)

        # 更新配置
        if self.current_config:
            self.current_config.submissions_dir = Path(self.file_path)
            self.current_config.suspicious_threshold = self.suspicious_spin.value()
            self.current_config.plagiarism_threshold = self.plagiarism_spin.value()

        self.plagiarism_service.start_detection(self.current_config)

    def _on_pause_detection(self):
        """暂停检测"""
        if self.plagiarism_service.is_paused():
            self.plagiarism_service.resume_detection()
            self.pause_btn.setText("⏸️ 暂停")
        else:
            self.plagiarism_service.pause_detection()
            self.pause_btn.setText("▶️ 继续")

    def _on_stop_detection(self):
        """停止检测"""
        self.plagiarism_service.stop_detection()
        self._reset_ui()

    def _on_progress_updated(self, progress: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def _on_detection_finished(self, results: dict):
        """检测完成"""
        self._reset_ui()
        self.export_btn.setEnabled(True)

        # 更新统计
        total = results.get('total_students', 0)
        suspicious = results.get('suspicious_count', 0)
        plagiarism = results.get('plagiarism_count', 0)
        max_sim = results.get('max_similarity', 0.0)

        self.total_label.setText(f"检测人数: {total}")
        self.suspicious_label.setText(f"可疑对数: {suspicious}")
        self.plagiarism_label.setText(f"涉嫌人数: {plagiarism}")
        self.max_label.setText(f"最高相似度: {max_sim:.1f}%")

        # 显示结果
        self._display_results(results)

        self.status_changed.emit(f"查重检测完成 - 检测 {total} 人，发现 {suspicious} 个可疑对")

    def _on_detection_failed(self, error: str):
        """检测失败"""
        self._reset_ui()
        self._show_error(f"检测失败: {error}")

    def _on_log_message(self, message: str):
        """日志消息"""
        self.log_text.append(message)

    def _display_results(self, results: dict):
        """显示检测结果"""
        pairs = results.get('similarity_pairs', [])

        self.result_table.setRowCount(0)

        for i, pair in enumerate(pairs):
            # 只显示相似度 > 50% 的结果
            if pair.get('overall_similarity', 0) < 50:
                continue

            self.result_table.insertRow(i)

            # 学生1
            self.result_table.setItem(i, 0, QTableWidgetItem(str(pair.get('student_id_1', ''))))
            self.result_table.setItem(i, 1, QTableWidgetItem(str(pair.get('name_1', ''))))

            # 学生2
            self.result_table.setItem(i, 2, QTableWidgetItem(str(pair.get('student_id_2', ''))))
            self.result_table.setItem(i, 3, QTableWidgetItem(str(pair.get('name_2', ''))))

            # 相似度
            similarity = pair.get('overall_similarity', 0)
            similarity_item = QTableWidgetItem(f"{similarity:.1f}%")

            # 根据相似度设置颜色
            if similarity >= 85:
                similarity_item.setBackground(QColor(0xf8d7da))  # 红色背景
            elif similarity >= 70:
                similarity_item.setBackground(QColor(0xfff3cd))  # 黄色背景
            elif similarity >= 60:
                similarity_item.setBackground(QColor(0xe2e3e5))  # 灰色背景

            self.result_table.setItem(i, 4, similarity_item)

            # 类型
            is_cross_group = pair.get('is_cross_group', False)
            type_text = "跨组" if is_cross_group else "同组"
            self.result_table.setItem(i, 5, QTableWidgetItem(type_text))

            # 状态
            if similarity >= 85:
                status = "抄袭"
                status_color = QColor(0xdc3545)
            elif similarity >= 70:
                status = "高相似"
                status_color = QColor(0xffc107)
            elif similarity >= 60:
                status = "可疑"
                status_color = QColor(0xfd7e14)
            else:
                status = "正常"
                status_color = QColor(0x28a745)

            status_item = QTableWidgetItem(status)
            status_item.setForeground(QBrush(status_color))
            self.result_table.setItem(i, 6, status_item)

    def _on_export_report(self):
        """导出报告"""
        # TODO: 实现报告导出
        self.status_changed.emit("报告导出功能开发中...")

    def _on_clear_results(self):
        """清空结果"""
        self.result_table.setRowCount(0)
        self.export_btn.setEnabled(False)
        self.log_text.clear()
        self.total_label.setText("检测人数: 0")
        self.suspicious_label.setText("可疑对数: 0")
        self.plagiarism_label.setText("涉嫌人数: 0")
        self.max_label.setText("最高相似度: 0%")
        self.progress_bar.setValue(0)
        self.status_label.setText("就绪")

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ 暂停")

    def _show_error(self, message: str):
        """显示错误消息"""
        self.log_text.append(f"❌ 错误: {message}")
        self.status_label.setText(message)

    def set_config(self, config: ProjectConfig):
        """设置项目配置"""
        self.current_config = config

        # 更新UI显示配置值
        self.suspicious_spin.setValue(config.suspicious_threshold)
        self.plagiarism_spin.setValue(config.plagiarism_threshold)

        if config.submissions_dir:
            self.file_label.setText(str(config.submissions_dir))
            self.file_path = str(config.submissions_dir)
