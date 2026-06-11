"""
设置视图

提供应用设置的界面
"""

from pathlib import Path
from typing import Optional
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QCheckBox,
    QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QGridLayout, QLineEdit, QTabWidget, QScrollArea,
    QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal

from app.models.domain import ProjectConfig, SimilarityWeights


class SettingsView(QWidget):
    """设置视图"""

    # 信号
    config_changed = pyqtSignal(object)  # 配置变化
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)

        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                color: #495057;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #3498db;
                font-weight: bold;
            }
        """)

        # 项目设置标签页
        project_tab = self._create_project_settings_tab()
        tab_widget.addTab(project_tab, "📁 项目设置")

        # 查重设置标签页
        plagiarism_tab = self._create_plagiarism_settings_tab()
        tab_widget.addTab(plagiarism_tab, "🔍 查重设置")

        # 评分设置标签页
        grading_tab = self._create_grading_settings_tab()
        tab_widget.addTab(grading_tab, "📝 评分设置")

        # 系统设置标签页
        system_tab = self._create_system_settings_tab()
        tab_widget.addTab(system_tab, "⚙️ 系统设置")

        content_layout.addWidget(tab_widget)

        # 保存按钮
        button_layout = QHBoxLayout()

        self.reset_btn = QPushButton("🔄 重置为默认")
        self.reset_btn.clicked.connect(self._on_reset)

        self.save_btn = QPushButton("💾 保存设置")
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 30px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.save_btn.clicked.connect(self._on_save)

        button_layout.addStretch()
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.save_btn)

        content_layout.addLayout(button_layout)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_project_settings_tab(self) -> QWidget:
        """创建项目设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_group.setStyleSheet("""
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

        basic_layout = QGridLayout()

        basic_layout.addWidget(QLabel("班级名称:"), 0, 0)
        self.class_name_edit = QLineEdit()
        self.class_name_edit.setPlaceholderText("例如: 汽服2302B班")
        basic_layout.addWidget(self.class_name_edit, 0, 1)

        basic_layout.addWidget(QLabel("实验类型:"), 1, 0)
        self.experiment_type_combo = QComboBox()
        self.experiment_type_combo.addItem("档位实验", "档位实验")
        self.experiment_type_combo.addItem("转向灯实验", "转向灯实验")
        self.experiment_type_combo.addItem("PWM LED实验", "PWM LED实验")
        self.experiment_type_combo.addItem("串口通信实验", "串口通信实验")
        self.experiment_type_combo.addItem("ADC采集实验", "ADC采集实验")
        self.experiment_type_combo.addItem("定时器实验", "定时器实验")
        self.experiment_type_combo.addItem("自定义", "自定义")
        basic_layout.addWidget(self.experiment_type_combo, 1, 1)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # 路径配置
        path_group = QGroupBox("路径配置")
        path_layout = QGridLayout()

        path_layout.addWidget(QLabel("实验目录:"), 0, 0)
        self.experiment_dir_edit = QLineEdit()
        self.experiment_dir_edit.setPlaceholderText("项目实验代码目录")
        experiment_btn = QPushButton("📂 浏览")
        experiment_btn.clicked.connect(self._on_select_experiment_dir)
        path_layout.addWidget(self.experiment_dir_edit, 0, 1)
        path_layout.addWidget(experiment_btn, 0, 2)

        path_layout.addWidget(QLabel("提交目录:"), 1, 0)
        self.submissions_dir_edit = QLineEdit()
        self.submissions_dir_edit.setPlaceholderText("学生提交ZIP文件目录")
        submissions_btn = QPushButton("📂 浏览")
        submissions_btn.clicked.connect(self._on_select_submissions_dir)
        path_layout.addWidget(self.submissions_dir_edit, 1, 1)
        path_layout.addWidget(submissions_btn, 1, 2)

        path_layout.addWidget(QLabel("输出目录:"), 2, 0)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("报告输出目录")
        output_btn = QPushButton("📂 浏览")
        output_btn.clicked.connect(self._on_select_output_dir)
        path_layout.addWidget(self.output_dir_edit, 2, 1)
        path_layout.addWidget(output_btn, 2, 2)

        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 模板配置
        template_group = QGroupBox("模板配置")
        template_layout = QGridLayout()

        template_layout.addWidget(QLabel("报告模板:"), 0, 0)
        self.template_path_edit = QLineEdit()
        self.template_path_edit.setPlaceholderText("实验报告模板文件（可选）")
        template_btn = QPushButton("📂 浏览")
        template_btn.clicked.connect(self._on_select_template)
        template_layout.addWidget(self.template_path_edit, 0, 1)
        template_layout.addWidget(template_btn, 0, 2)

        template_layout.addWidget(QLabel("Rubric文件:"), 1, 0)
        self.rubric_path_edit = QLineEdit()
        self.rubric_path_edit.setPlaceholderText("评分标准文件（可选）")
        rubric_btn = QPushButton("📂 浏览")
        rubric_btn.clicked.connect(self._on_select_rubric)
        template_layout.addWidget(self.rubric_path_edit, 1, 1)
        template_layout.addWidget(rubric_btn, 1, 2)

        template_group.setLayout(template_layout)
        layout.addWidget(template_group)

        layout.addStretch()

        return widget

    def _create_plagiarism_settings_tab(self) -> QWidget:
        """创建查重设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 阈值配置
        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setStyleSheet("""
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

        threshold_layout = QGridLayout()

        threshold_layout.addWidget(QLabel("可疑阈值:"), 0, 0)
        self.suspicious_threshold_spin = QDoubleSpinBox()
        self.suspicious_threshold_spin.setRange(0, 100)
        self.suspicious_threshold_spin.setValue(60)
        self.suspicious_threshold_spin.setSuffix("%")
        self.suspicious_threshold_spin.setToolTip("超过此值将被标记为可疑")
        threshold_layout.addWidget(self.suspicious_threshold_spin, 0, 1)

        threshold_layout.addWidget(QLabel("高相似度阈值:"), 1, 0)
        self.high_similarity_threshold_spin = QDoubleSpinBox()
        self.high_similarity_threshold_spin.setRange(0, 100)
        self.high_similarity_threshold_spin.setValue(70)
        self.high_similarity_threshold_spin.setSuffix("%")
        threshold_layout.addWidget(self.high_similarity_threshold_spin, 1, 1)

        threshold_layout.addWidget(QLabel("抄袭阈值:"), 2, 0)
        self.plagiarism_threshold_spin = QDoubleSpinBox()
        self.plagiarism_threshold_spin.setRange(0, 100)
        self.plagiarism_threshold_spin.setValue(85)
        self.plagiarism_threshold_spin.setSuffix("%")
        self.plagiarism_threshold_spin.setToolTip("超过此值将被标记为抄袭")
        threshold_layout.addWidget(self.plagiarism_threshold_spin, 2, 1)

        threshold_group.setLayout(threshold_layout)
        layout.addWidget(threshold_group)

        # 权重配置
        weight_group = QGroupBox("相似度权重")
        weight_layout = QGridLayout()

        weight_layout.addWidget(QLabel("文本相似度:"), 0, 0)
        self.text_weight_spin = QDoubleSpinBox()
        self.text_weight_spin.setRange(0, 1)
        self.text_weight_spin.setSingleStep(0.05)
        self.text_weight_spin.setValue(0.5)
        weight_layout.addWidget(self.text_weight_spin, 0, 1)

        weight_layout.addWidget(QLabel("代码相似度:"), 1, 0)
        self.code_weight_spin = QDoubleSpinBox()
        self.code_weight_spin.setRange(0, 1)
        self.code_weight_spin.setSingleStep(0.05)
        self.code_weight_spin.setValue(0.3)
        weight_layout.addWidget(self.code_weight_spin, 1, 1)

        weight_layout.addWidget(QLabel("结构相似度:"), 2, 0)
        self.structure_weight_spin = QDoubleSpinBox()
        self.structure_weight_spin.setRange(0, 1)
        self.structure_weight_spin.setSingleStep(0.05)
        self.structure_weight_spin.setValue(0.1)
        weight_layout.addWidget(self.structure_weight_spin, 2, 1)

        weight_layout.addWidget(QLabel("语义相似度:"), 3, 0)
        self.semantic_weight_spin = QDoubleSpinBox()
        self.semantic_weight_spin.setRange(0, 1)
        self.semantic_weight_spin.setSingleStep(0.05)
        self.semantic_weight_spin.setValue(0.1)
        weight_layout.addWidget(self.semantic_weight_spin, 3, 1)

        # 验证权重总和
        self.weight_sum_label = QLabel("权重总和: 1.00")
        self.weight_sum_label.setStyleSheet("color: #28a745; font-weight: bold;")
        weight_layout.addWidget(self.weight_sum_label, 4, 0, 1, 2)

        # 连接权重变化信号
        for spin in [self.text_weight_spin, self.code_weight_spin,
                     self.structure_weight_spin, self.semantic_weight_spin]:
            spin.valueChanged.connect(self._update_weight_sum)

        weight_group.setLayout(weight_layout)
        layout.addWidget(weight_group)

        # 检测选项
        options_group = QGroupBox("检测选项")
        options_layout = QVBoxLayout()

        self.enable_template_filter_cb = QCheckBox("启用模板内容过滤")
        self.enable_template_filter_cb.setChecked(True)
        self.enable_semantic_cb = QCheckBox("启用语义相似度检测")
        self.enable_semantic_cb.setChecked(True)
        self.enable_jieba_cb = QCheckBox("启用中文分词")
        self.enable_jieba_cb.setChecked(True)
        self.enable_code_obfuscation_cb = QCheckBox("启用代码混淆检测")
        self.enable_code_obfuscation_cb.setChecked(False)

        options_layout.addWidget(self.enable_template_filter_cb)
        options_layout.addWidget(self.enable_semantic_cb)
        options_layout.addWidget(self.enable_jieba_cb)
        options_layout.addWidget(self.enable_code_obfuscation_cb)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        layout.addStretch()

        return widget

    def _create_grading_settings_tab(self) -> QWidget:
        """创建评分设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 评分选项
        options_group = QGroupBox("评分选项")
        options_group.setStyleSheet("""
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

        options_layout = QVBoxLayout()

        self.enable_rubric_grading_cb = QCheckBox("启用Rubric评分")
        self.enable_rubric_grading_cb.setChecked(True)
        self.enable_technical_check_cb = QCheckBox("启用技术要点检查")
        self.enable_technical_check_cb.setChecked(True)
        self.enable_code_analysis_cb = QCheckBox("启用代码深度分析")
        self.enable_code_analysis_cb.setChecked(True)
        self.enable_image_quality_cb = QCheckBox("启用图像质量检测")
        self.enable_image_quality_cb.setChecked(True)
        self.enable_consistency_cb = QCheckBox("启用评分一致性校验")
        self.enable_consistency_cb.setChecked(False)

        options_layout.addWidget(self.enable_rubric_grading_cb)
        options_layout.addWidget(self.enable_technical_check_cb)
        options_layout.addWidget(self.enable_code_analysis_cb)
        options_layout.addWidget(self.enable_image_quality_cb)
        options_layout.addWidget(self.enable_consistency_cb)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # 分数配置
        score_group = QGroupBox("分数配置")
        score_layout = QGridLayout()

        score_layout.addWidget(QLabel("满分:"), 0, 0)
        self.max_score_spin = QDoubleSpinBox()
        self.max_score_spin.setRange(0, 200)
        self.max_score_spin.setValue(100)
        self.max_score_spin.setSuffix("分")
        score_layout.addWidget(self.max_score_spin, 0, 1)

        score_layout.addWidget(QLabel("及格分数:"), 1, 0)
        self.pass_score_spin = QDoubleSpinBox()
        self.pass_score_spin.setRange(0, 200)
        self.pass_score_spin.setValue(60)
        self.pass_score_spin.setSuffix("分")
        score_layout.addWidget(self.pass_score_spin, 1, 1)

        # 等级配置
        score_layout.addWidget(QLabel("优秀分数线 (A):"), 2, 0)
        self.grade_a_spin = QDoubleSpinBox()
        self.grade_a_spin.setRange(0, 100)
        self.grade_a_spin.setValue(90)
        self.grade_a_spin.setSuffix("%")
        score_layout.addWidget(self.grade_a_spin, 2, 1)

        score_layout.addWidget(QLabel("良好分数线 (B):"), 3, 0)
        self.grade_b_spin = QDoubleSpinBox()
        self.grade_b_spin.setRange(0, 100)
        self.grade_b_spin.setValue(80)
        self.grade_b_spin.setSuffix("%")
        score_layout.addWidget(self.grade_b_spin, 3, 1)

        score_layout.addWidget(QLabel("中等分数线 (C):"), 4, 0)
        self.grade_c_spin = QDoubleSpinBox()
        self.grade_c_spin.setRange(0, 100)
        self.grade_c_spin.setValue(70)
        self.grade_c_spin.setSuffix("%")
        score_layout.addWidget(self.grade_c_spin, 4, 1)

        score_layout.addWidget(QLabel("及格分数线 (D):"), 5, 0)
        self.grade_d_spin = QDoubleSpinBox()
        self.grade_d_spin.setRange(0, 100)
        self.grade_d_spin.setValue(60)
        self.grade_d_spin.setSuffix("%")
        score_layout.addWidget(self.grade_d_spin, 5, 1)

        score_group.setLayout(score_layout)
        layout.addWidget(score_group)

        layout.addStretch()

        return widget

    def _create_system_settings_tab(self) -> QWidget:
        """创建系统设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_group.setStyleSheet("""
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

        ui_layout = QVBoxLayout()

        self.dark_mode_cb = QCheckBox("深色模式")
        self.compact_mode_cb = QCheckBox("紧凑模式")
        self.show_tooltips_cb = QCheckBox("显示工具提示")
        self.show_tooltips_cb.setChecked(True)

        ui_layout.addWidget(self.dark_mode_cb)
        ui_layout.addWidget(self.compact_mode_cb)
        ui_layout.addWidget(self.show_tooltips_cb)

        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)

        # 性能设置
        perf_group = QGroupBox("性能设置")
        perf_layout = QGridLayout()

        perf_layout.addWidget(QLabel("线程数:"), 0, 0)
        self.thread_count_spin = QSpinBox()
        self.thread_count_spin.setRange(1, 16)
        self.thread_count_spin.setValue(4)
        perf_layout.addWidget(self.thread_count_spin, 0, 1)

        perf_layout.addWidget(QLabel("缓存大小:"), 1, 0)
        self.cache_size_spin = QSpinBox()
        self.cache_size_spin.setRange(10, 1000)
        self.cache_size_spin.setValue(100)
        self.cache_size_spin.setSuffix(" MB")
        perf_layout.addWidget(self.cache_size_spin, 1, 1)

        perf_group.setLayout(perf_layout)
        layout.addWidget(perf_group)

        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QVBoxLayout()

        self.enable_log_cb = QCheckBox("启用日志记录")
        self.enable_log_cb.setChecked(True)

        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("日志级别:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItem("调试", "DEBUG")
        self.log_level_combo.addItem("信息", "INFO")
        self.log_level_combo.addItem("警告", "WARNING")
        self.log_level_combo.addItem("错误", "ERROR")
        self.log_level_combo.setCurrentIndex(1)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        log_layout.addWidget(self.enable_log_cb)
        log_layout.addLayout(log_level_layout)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 关于
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout()

        about_text = """
        <h3>STM32教学管理系统</h3>
        <p>版本: 1.0.0</p>
        <p>用于STM32F407嵌入式教学的桌面GUI应用</p>
        <p>功能: 查重检测、评分评估、反馈生成、报告输出</p>
        """

        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)

        about_group.setLayout(about_layout)
        layout.addWidget(about_group)

        layout.addStretch()

        return widget

    def _update_weight_sum(self):
        """更新权重总和"""
        total = (self.text_weight_spin.value() +
                self.code_weight_spin.value() +
                self.structure_weight_spin.value() +
                self.semantic_weight_spin.value())

        self.weight_sum_label.setText(f"权重总和: {total:.2f}")

        if abs(total - 1.0) < 0.01:
            self.weight_sum_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.weight_sum_label.setStyleSheet("color: #dc3545; font-weight: bold;")

    def _on_select_experiment_dir(self):
        """选择实验目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择实验目录")
        if directory:
            self.experiment_dir_edit.setText(directory)

    def _on_select_submissions_dir(self):
        """选择提交目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择提交目录")
        if directory:
            self.submissions_dir_edit.setText(directory)

    def _on_select_output_dir(self):
        """选择输出目录"""
        directory = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if directory:
            self.output_dir_edit.setText(directory)

    def _on_select_template(self):
        """选择模板文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模板文件",
            "",
            "所有文件 (*.*)"
        )
        if file_path:
            self.template_path_edit.setText(file_path)

    def _on_select_rubric(self):
        """选择Rubric文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择Rubric文件",
            "",
            "JSON文件 (*.json)"
        )
        if file_path:
            self.rubric_path_edit.setText(file_path)

    def _on_reset(self):
        """重置为默认值"""
        # 项目设置
        self.class_name_edit.clear()
        self.experiment_dir_edit.clear()
        self.submissions_dir_edit.clear()
        self.output_dir_edit.clear()
        self.template_path_edit.clear()
        self.rubric_path_edit.clear()

        # 查重设置
        self.suspicious_threshold_spin.setValue(60)
        self.high_similarity_threshold_spin.setValue(70)
        self.plagiarism_threshold_spin.setValue(85)
        self.text_weight_spin.setValue(0.5)
        self.code_weight_spin.setValue(0.3)
        self.structure_weight_spin.setValue(0.1)
        self.semantic_weight_spin.setValue(0.1)

        # 评分设置
        self.max_score_spin.setValue(100)
        self.pass_score_spin.setValue(60)

        self.status_changed.emit("设置已重置为默认值")

    def _on_save(self):
        """保存设置"""
        if self.current_config:
            # 更新配置
            self.current_config.class_name = self.class_name_edit.text()
            self.current_config.experiment_type = self.experiment_type_combo.currentData()

            if self.experiment_dir_edit.text():
                self.current_config.experiment_dir = Path(self.experiment_dir_edit.text())
            if self.submissions_dir_edit.text():
                self.current_config.submissions_dir = Path(self.submissions_dir_edit.text())
            if self.output_dir_edit.text():
                self.current_config.output_dir = Path(self.output_dir_edit.text())
            if self.template_path_edit.text():
                self.current_config.template_path = Path(self.template_path_edit.text())
            if self.rubric_path_edit.text():
                self.current_config.rubric_path = Path(self.rubric_path_edit.text())

            # 查重设置
            self.current_config.suspicious_threshold = self.suspicious_threshold_spin.value()
            self.current_config.high_similarity_threshold = self.high_similarity_threshold_spin.value()
            self.current_config.plagiarism_threshold = self.plagiarism_threshold_spin.value()

            self.current_config.weights = SimilarityWeights(
                text=self.text_weight_spin.value(),
                code=self.code_weight_spin.value(),
                structure=self.structure_weight_spin.value(),
                semantic=self.semantic_weight_spin.value()
            )

            self.config_changed.emit(self.current_config)
            self.status_changed.emit("设置已保存")

    def set_config(self, config: ProjectConfig):
        """设置配置"""
        self.current_config = config

        # 更新UI显示
        self.class_name_edit.setText(config.class_name)
        self.experiment_type_combo.setCurrentText(config.experiment_type.value)
        self.experiment_dir_edit.setText(str(config.experiment_dir))

        if config.submissions_dir:
            self.submissions_dir_edit.setText(str(config.submissions_dir))
        if config.output_dir:
            self.output_dir_edit.setText(str(config.output_dir))
        if config.template_path:
            self.template_path_edit.setText(str(config.template_path))
        if config.rubric_path:
            self.rubric_path_edit.setText(str(config.rubric_path))

        # 查重设置
        self.suspicious_threshold_spin.setValue(config.suspicious_threshold)
        self.high_similarity_threshold_spin.setValue(config.high_similarity_threshold)
        self.plagiarism_threshold_spin.setValue(config.plagiarism_threshold)

        self.text_weight_spin.setValue(config.weights.text)
        self.code_weight_spin.setValue(config.weights.code)
        self.structure_weight_spin.setValue(config.weights.structure)
        self.semantic_weight_spin.setValue(config.weights.semantic)
