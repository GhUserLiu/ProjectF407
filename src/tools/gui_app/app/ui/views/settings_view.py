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
from app.ui.file_dialog_utils import get_existing_directory, get_open_filename, get_save_filename


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

        self.import_btn = QPushButton("📥 导入配置")
        self.import_btn.clicked.connect(self._on_import_config)

        self.export_btn = QPushButton("📤 导出配置")
        self.export_btn.clicked.connect(self._on_export_config)

        self.backup_btn = QPushButton("💾 备份数据")
        self.backup_btn.setToolTip("备份项目配置和处理结果")
        self.backup_btn.clicked.connect(self._on_backup_data)

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
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.backup_btn)
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
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(300)
        self.template_combo.addItem("— 无 —", "")
        # 扫描默认模板目录
        self._scan_templates()
        template_refresh_btn = QPushButton("🔄")
        template_refresh_btn.setToolTip("重新扫描模板文件")
        template_refresh_btn.setMaximumWidth(40)
        template_refresh_btn.clicked.connect(self._scan_templates)
        template_layout.addWidget(self.template_combo, 0, 1)
        template_layout.addWidget(template_refresh_btn, 0, 2)

        template_layout.addWidget(QLabel("Rubric文件:"), 1, 0)
        self.rubric_combo = QComboBox()
        self.rubric_combo.setMinimumWidth(300)
        self.rubric_combo.addItem("— 无 —", "")
        # 扫描默认 rubric 目录
        self._scan_rubrics()
        rubric_refresh_btn = QPushButton("🔄")
        rubric_refresh_btn.setToolTip("重新扫描Rubric文件")
        rubric_refresh_btn.setMaximumWidth(40)
        rubric_refresh_btn.clicked.connect(self._scan_rubrics)
        template_layout.addWidget(self.rubric_combo, 1, 1)
        template_layout.addWidget(rubric_refresh_btn, 1, 2)

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
        <p>版本: 2.7.0</p>
        <p>用于STM32F407嵌入式教学的桌面GUI应用</p>
        <p>功能: 查重检测、评分评估、反馈生成、报告输出</p>
        <hr style="margin: 10px 0;">
        <p style="color: #6c757d; font-size: 12px;">
        <b>技术支持：</b><br>
        如使用中发现故障，请提供触发故障的行为及故障现象<br>
        通过邮箱与作者联系：<br>
        <a href="mailto:liuzhaoqi@sxgkd.edu.cn" style="color: #3498db;">liuzhaoqi@sxgkd.edu.cn</a>
        </p>
        """

        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_label.setOpenExternalLinks(True)
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
        # 优先定位到教学演示目录（如果存在）
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir and (data_dir / 'teaching_demo').exists():
            DialogStartDir._last_dirs['submission'] = str(data_dir / 'teaching_demo')

        directory = get_existing_directory(
            self,
            "选择实验目录",
            'submission',
            self.current_config
        )
        if directory:
            self.experiment_dir_edit.setText(directory)

    def _on_select_submissions_dir(self):
        """选择提交目录"""
        # 优先定位到测试提交目录（如果存在）
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            # 检查 teaching_demo 中的 submissions
            teaching_subs = data_dir / 'teaching_demo' / '2026-春季' / '汽服2302B班' / '07-car-gear' / 'submissions'
            if teaching_subs.exists():
                DialogStartDir._last_dirs['submission'] = str(teaching_subs)
            # 检查测试数据中的 submissions
            elif (data_dir / 'submissions').exists():
                DialogStartDir._last_dirs['submission'] = str(data_dir / 'submissions')

        directory = get_existing_directory(
            self,
            "选择提交目录",
            'submission',
            self.current_config
        )
        if directory:
            self.submissions_dir_edit.setText(directory)

    def _on_select_output_dir(self):
        """选择输出目录"""
        # 优先定位到测试结果目录（如果存在）
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir and (data_dir / 'results').exists():
            DialogStartDir._last_dirs['output'] = str(data_dir / 'results')

        directory = get_existing_directory(
            self,
            "选择输出目录",
            'output',
            self.current_config
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def _scan_templates(self):
        """扫描可用的模板文件"""
        from app.ui.file_dialog_utils import DialogStartDir

        # 保存当前选择
        current_data = self.template_combo.currentData()

        self.template_combo.clear()
        self.template_combo.addItem("— 无 —", "")

        # 扫描默认模板目录
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            template_dir = data_dir / 'templates'
            if template_dir.exists():
                # 扫描 docx 和 md 文件
                for file in sorted(template_dir.glob('*.docx')):
                    self.template_combo.addItem(f"{file.name} (Word)", str(file))
                for file in sorted(template_dir.glob('*.md')):
                    self.template_combo.addItem(f"{file.name} (Markdown)", str(file))

        # 恢复之前的选择
        if current_data:
            for i in range(self.template_combo.count()):
                if self.template_combo.itemData(i) == current_data:
                    self.template_combo.setCurrentIndex(i)
                    break

    def _scan_rubrics(self):
        """扫描可用的Rubric文件"""
        from app.ui.file_dialog_utils import DialogStartDir

        # 保存当前选择
        current_data = self.rubric_combo.currentData()

        self.rubric_combo.clear()
        self.rubric_combo.addItem("— 无 —", "")

        # 扫描默认 rubric 目录
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            rubric_dir = data_dir / 'rubrics'
            if rubric_dir.exists():
                # 扫描 json 文件
                for file in sorted(rubric_dir.glob('*.json')):
                    self.rubric_combo.addItem(file.name, str(file))

        # 恢复之前的选择
        if current_data:
            for i in range(self.rubric_combo.count()):
                if self.rubric_combo.itemData(i) == current_data:
                    self.rubric_combo.setCurrentIndex(i)
                    break

    def _on_select_template(self):
        """手动选择模板文件（添加到下拉框）"""
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            if (data_dir / 'templates').exists():
                DialogStartDir._last_dirs['template'] = str(data_dir / 'templates')

        file_path, _ = get_open_filename(
            self,
            "选择模板文件",
            "Word文档 (*.docx);;Markdown文档 (*.md);;所有文件 (*.*)",
            'template',
            self.current_config
        )
        if file_path:
            # 添加到下拉框并选中
            file_name = Path(file_path).name
            if file_path.endswith('.docx'):
                file_name = f"{file_name} (Word)"
            elif file_path.endswith('.md'):
                file_name = f"{file_name} (Markdown)"

            # 检查是否已存在
            exists = False
            for i in range(self.template_combo.count()):
                if self.template_combo.itemData(i) == file_path:
                    self.template_combo.setCurrentIndex(i)
                    exists = True
                    break

            if not exists:
                self.template_combo.addItem(file_name, file_path)
                self.template_combo.setCurrentIndex(self.template_combo.count() - 1)

    def _on_select_rubric(self):
        """手动选择Rubric文件（添加到下拉框）"""
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            if (data_dir / 'rubrics').exists():
                DialogStartDir._last_dirs['rubric'] = str(data_dir / 'rubrics')

        file_path, _ = get_open_filename(
            self,
            "选择Rubric文件",
            "JSON文件 (*.json);;所有文件 (*.*)",
            'rubric',
            self.current_config
        )
        if file_path:
            file_name = Path(file_path).name

            # 检查是否已存在
            exists = False
            for i in range(self.rubric_combo.count()):
                if self.rubric_combo.itemData(i) == file_path:
                    self.rubric_combo.setCurrentIndex(i)
                    exists = True
                    break

            if not exists:
                self.rubric_combo.addItem(file_name, file_path)
                self.rubric_combo.setCurrentIndex(self.rubric_combo.count() - 1)

    def _on_reset(self):
        """重置为默认值"""
        # 项目设置
        self.class_name_edit.clear()
        self.experiment_dir_edit.clear()
        self.submissions_dir_edit.clear()
        self.output_dir_edit.clear()
        # 重置下拉框到默认值（第一项"— 无 —"）
        self.template_combo.setCurrentIndex(0)
        self.rubric_combo.setCurrentIndex(0)

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
            # 从下拉框获取选择的模板和 Rubric 文件路径
            template_path = self.template_combo.currentData()
            if template_path:
                self.current_config.template_path = Path(template_path)
            rubric_path = self.rubric_combo.currentData()
            if rubric_path:
                self.current_config.rubric_path = Path(rubric_path)

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
        import sys
        print(f"[DEBUG] settings_view.set_config called with config type: {type(config)}", file=sys.stderr)
        print(f"[DEBUG] config has weights: {hasattr(config, 'weights')}", file=sys.stderr)
        if hasattr(config, 'weights'):
            print(f"[DEBUG] config.weights type: {type(config.weights)}", file=sys.stderr)
            print(f"[DEBUG] config.weights value: {config.weights}", file=sys.stderr)

        self.current_config = config

        # 更新UI显示
        self.class_name_edit.setText(config.class_name)
        self.experiment_type_combo.setCurrentText(config.experiment_type.value)
        self.experiment_dir_edit.setText(str(config.experiment_dir))

        if config.submissions_dir:
            self.submissions_dir_edit.setText(str(config.submissions_dir))
        if config.output_dir:
            self.output_dir_edit.setText(str(config.output_dir))

        # 更新模板和 Rubric 下拉框选择
        if config.template_path:
            template_path_str = str(config.template_path)
            for i in range(self.template_combo.count()):
                if self.template_combo.itemData(i) == template_path_str:
                    self.template_combo.setCurrentIndex(i)
                    break

        if config.rubric_path:
            rubric_path_str = str(config.rubric_path)
            for i in range(self.rubric_combo.count()):
                if self.rubric_combo.itemData(i) == rubric_path_str:
                    self.rubric_combo.setCurrentIndex(i)
                    break

        # 查重设置
        print(f"[DEBUG] Setting threshold values...", file=sys.stderr)
        self.suspicious_threshold_spin.setValue(config.suspicious_threshold)
        self.high_similarity_threshold_spin.setValue(config.high_similarity_threshold)
        self.plagiarism_threshold_spin.setValue(config.plagiarism_threshold)

        print(f"[DEBUG] Setting weight values...", file=sys.stderr)
        print(f"[DEBUG] config.weights.text type: {type(config.weights.text)}", file=sys.stderr)
        self.text_weight_spin.setValue(config.weights.text)
        self.code_weight_spin.setValue(config.weights.code)
        self.structure_weight_spin.setValue(config.weights.structure)
        self.semantic_weight_spin.setValue(config.weights.semantic)
        print(f"[DEBUG] set_config completed", file=sys.stderr)

    def _on_export_config(self):
        """导出配置到文件"""
        file_path, _ = get_save_filename(
            self,
            "导出配置文件",
            "JSON文件 (*.json)",
            'export',
            self.current_config,
            default_name="stm32_config.json"
        )

        if file_path:
            try:
                # 收集当前所有设置
                config_data = {
                    "version": "2.6.0",
                    "project": {
                        "class_name": self.class_name_edit.text(),
                        "experiment_type": self.experiment_type_combo.currentData(),
                        "experiment_dir": self.experiment_dir_edit.text(),
                        "submissions_dir": self.submissions_dir_edit.text(),
                        "output_dir": self.output_dir_edit.text(),
                        "template_path": self.template_combo.currentData() or "",
                        "rubric_path": self.rubric_combo.currentData() or "",
                    },
                    "plagiarism": {
                        "suspicious_threshold": self.suspicious_threshold_spin.value(),
                        "high_similarity_threshold": self.high_similarity_threshold_spin.value(),
                        "plagiarism_threshold": self.plagiarism_threshold_spin.value(),
                        "weights": {
                            "text": self.text_weight_spin.value(),
                            "code": self.code_weight_spin.value(),
                            "structure": self.structure_weight_spin.value(),
                            "semantic": self.semantic_weight_spin.value(),
                        },
                        "enable_template_filter": self.enable_template_filter_cb.isChecked(),
                        "enable_semantic": self.enable_semantic_cb.isChecked(),
                        "enable_jieba": self.enable_jieba_cb.isChecked(),
                        "enable_code_obfuscation": self.enable_code_obfuscation_cb.isChecked(),
                    },
                    "grading": {
                        "enable_rubric": self.enable_rubric_grading_cb.isChecked(),
                        "enable_technical": self.enable_technical_check_cb.isChecked(),
                        "enable_code_analysis": self.enable_code_analysis_cb.isChecked(),
                        "enable_image_quality": self.enable_image_quality_cb.isChecked(),
                        "enable_consistency": self.enable_consistency_cb.isChecked(),
                        "max_score": self.max_score_spin.value(),
                        "pass_score": self.pass_score_spin.value(),
                        "grade_a": self.grade_a_spin.value(),
                        "grade_b": self.grade_b_spin.value(),
                        "grade_c": self.grade_c_spin.value(),
                        "grade_d": self.grade_d_spin.value(),
                    },
                    "system": {
                        "dark_mode": self.dark_mode_cb.isChecked(),
                        "compact_mode": self.compact_mode_cb.isChecked(),
                        "show_tooltips": self.show_tooltips_cb.isChecked(),
                        "thread_count": self.thread_count_spin.value(),
                        "cache_size": self.cache_size_spin.value(),
                        "enable_log": self.enable_log_cb.isChecked(),
                        "log_level": self.log_level_combo.currentData(),
                    }
                }

                # 保存到文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=2, ensure_ascii=False)

                self.status_changed.emit(f"配置已导出到: {file_path}")

            except Exception as e:
                self.status_changed.emit(f"导出失败: {str(e)}")

    def _on_import_config(self):
        """从文件导入配置"""
        file_path, _ = get_open_filename(
            self,
            "导入配置文件",
            "JSON文件 (*.json)",
            'config',
            self.current_config
        )

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 验证版本
                config_version = config_data.get("version", "1.0.0")
                if config_version != "2.6.0":
                    self.status_changed.emit(f"警告: 配置版本 {config_version} 可能不兼容")

                # 加载项目设置
                project = config_data.get("project", {})
                self.class_name_edit.setText(project.get("class_name", ""))
                self.experiment_dir_edit.setText(project.get("experiment_dir", ""))
                self.submissions_dir_edit.setText(project.get("submissions_dir", ""))
                self.output_dir_edit.setText(project.get("output_dir", ""))

                # 从配置文件加载模板路径
                template_path = project.get("template_path", "")
                if template_path:
                    # 检查是否在下拉框中
                    found = False
                    for i in range(self.template_combo.count()):
                        if self.template_combo.itemData(i) == template_path:
                            self.template_combo.setCurrentIndex(i)
                            found = True
                            break
                    # 如果不在下拉框中，添加并选择
                    if not found:
                        from pathlib import Path as FilePath
                        file_name = FilePath(template_path).name
                        if template_path.endswith('.docx'):
                            file_name = f"{file_name} (Word)"
                        elif template_path.endswith('.md'):
                            file_name = f"{file_name} (Markdown)"
                        self.template_combo.addItem(file_name, template_path)
                        self.template_combo.setCurrentIndex(self.template_combo.count() - 1)

                # 从配置文件加载 Rubric 路径
                rubric_path = project.get("rubric_path", "")
                if rubric_path:
                    # 检查是否在下拉框中
                    found = False
                    for i in range(self.rubric_combo.count()):
                        if self.rubric_combo.itemData(i) == rubric_path:
                            self.rubric_combo.setCurrentIndex(i)
                            found = True
                            break
                    # 如果不在下拉框中，添加并选择
                    if not found:
                        from pathlib import Path as FilePath
                        file_name = FilePath(rubric_path).name
                        self.rubric_combo.addItem(file_name, rubric_path)
                        self.rubric_combo.setCurrentIndex(self.rubric_combo.count() - 1)

                exp_type = project.get("experiment_type", "档位实验")
                for i in range(self.experiment_type_combo.count()):
                    if self.experiment_type_combo.itemData(i) == exp_type:
                        self.experiment_type_combo.setCurrentIndex(i)
                        break

                # 加载查重设置
                plagiarism = config_data.get("plagiarism", {})
                self.suspicious_threshold_spin.setValue(plagiarism.get("suspicious_threshold", 60))
                self.high_similarity_threshold_spin.setValue(plagiarism.get("high_similarity_threshold", 70))
                self.plagiarism_threshold_spin.setValue(plagiarism.get("plagiarism_threshold", 85))

                weights = plagiarism.get("weights", {})
                self.text_weight_spin.setValue(weights.get("text", 0.5))
                self.code_weight_spin.setValue(weights.get("code", 0.3))
                self.structure_weight_spin.setValue(weights.get("structure", 0.1))
                self.semantic_weight_spin.setValue(weights.get("semantic", 0.1))

                self.enable_template_filter_cb.setChecked(plagiarism.get("enable_template_filter", True))
                self.enable_semantic_cb.setChecked(plagiarism.get("enable_semantic", True))
                self.enable_jieba_cb.setChecked(plagiarism.get("enable_jieba", True))
                self.enable_code_obfuscation_cb.setChecked(plagiarism.get("enable_code_obfuscation", False))

                # 加载评分设置
                grading = config_data.get("grading", {})
                self.enable_rubric_grading_cb.setChecked(grading.get("enable_rubric", True))
                self.enable_technical_check_cb.setChecked(grading.get("enable_technical", True))
                self.enable_code_analysis_cb.setChecked(grading.get("enable_code_analysis", True))
                self.enable_image_quality_cb.setChecked(grading.get("enable_image_quality", True))
                self.enable_consistency_cb.setChecked(grading.get("enable_consistency", False))
                self.max_score_spin.setValue(grading.get("max_score", 100))
                self.pass_score_spin.setValue(grading.get("pass_score", 60))
                self.grade_a_spin.setValue(grading.get("grade_a", 90))
                self.grade_b_spin.setValue(grading.get("grade_b", 80))
                self.grade_c_spin.setValue(grading.get("grade_c", 70))
                self.grade_d_spin.setValue(grading.get("grade_d", 60))

                # 加载系统设置
                system = config_data.get("system", {})
                self.dark_mode_cb.setChecked(system.get("dark_mode", False))
                self.compact_mode_cb.setChecked(system.get("compact_mode", False))
                self.show_tooltips_cb.setChecked(system.get("show_tooltips", True))
                self.thread_count_spin.setValue(system.get("thread_count", 4))
                self.cache_size_spin.setValue(system.get("cache_size", 100))
                self.enable_log_cb.setChecked(system.get("enable_log", True))

                log_level = system.get("log_level", "INFO")
                for i in range(self.log_level_combo.count()):
                    if self.log_level_combo.itemData(i) == log_level:
                        self.log_level_combo.setCurrentIndex(i)
                        break

                self.status_changed.emit(f"配置已从文件导入: {file_path}")

            except json.JSONDecodeError:
                self.status_changed.emit("错误: 无效的配置文件格式")
            except Exception as e:
                self.status_changed.emit(f"导入失败: {str(e)}")

    def _on_backup_data(self):
        """备份项目数据和结果"""
        if not self.current_config:
            self.status_changed.emit("错误: 没有加载的项目配置")
            return

        # 选择备份目录
        backup_dir = get_existing_directory(
            self,
            "选择备份目录",
            'export',
            self.current_config
        )

        if not backup_dir:
            return

        try:
            import zipfile
            import shutil
            from datetime import datetime

            # 创建备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.class_name_edit.text() or 'project'}_backup_{timestamp}"
            backup_path = Path(backup_dir) / f"{backup_name}.zip"

            # 收集需要备份的文件
            files_to_backup = []

            # 1. 配置文件
            config_content = {
                "version": "2.6.0",
                "project": {
                    "class_name": self.class_name_edit.text(),
                    "experiment_type": self.experiment_type_combo.currentData(),
                    "experiment_dir": self.experiment_dir_edit.text(),
                    "submissions_dir": self.submissions_dir_edit.text(),
                    "output_dir": self.output_dir_edit.text(),
                    "template_path": self.template_combo.currentData() or "",
                    "rubric_path": self.rubric_combo.currentData() or "",
                },
                "plagiarism": {
                    "suspicious_threshold": self.suspicious_threshold_spin.value(),
                    "high_similarity_threshold": self.high_similarity_threshold_spin.value(),
                    "plagiarism_threshold": self.plagiarism_threshold_spin.value(),
                    "weights": {
                        "text": self.text_weight_spin.value(),
                        "code": self.code_weight_spin.value(),
                        "structure": self.structure_weight_spin.value(),
                        "semantic": self.semantic_weight_spin.value(),
                    },
                    "enable_template_filter": self.enable_template_filter_cb.isChecked(),
                    "enable_semantic": self.enable_semantic_cb.isChecked(),
                    "enable_jieba": self.enable_jieba_cb.isChecked(),
                    "enable_code_obfuscation": self.enable_code_obfuscation_cb.isChecked(),
                },
                "grading": {
                    "enable_rubric": self.enable_rubric_grading_cb.isChecked(),
                    "enable_technical": self.enable_technical_check_cb.isChecked(),
                    "enable_code_analysis": self.enable_code_analysis_cb.isChecked(),
                    "enable_image_quality": self.enable_image_quality_cb.isChecked(),
                    "enable_consistency": self.enable_consistency_cb.isChecked(),
                    "max_score": self.max_score_spin.value(),
                    "pass_score": self.pass_score_spin.value(),
                    "grade_a": self.grade_a_spin.value(),
                    "grade_b": self.grade_b_spin.value(),
                    "grade_c": self.grade_c_spin.value(),
                    "grade_d": self.grade_d_spin.value(),
                }
            }

            # 2. 添加实际存在的文件
            existing_paths = []
            if self.experiment_dir_edit.text():
                exp_dir = Path(self.experiment_dir_edit.text())
                if exp_dir.exists():
                    existing_paths.append(("experiment", exp_dir))

            if self.submissions_dir_edit.text():
                sub_dir = Path(self.submissions_dir_edit.text())
                if sub_dir.exists():
                    existing_paths.append(("submissions", sub_dir))

            if self.output_dir_edit.text():
                out_dir = Path(self.output_dir_edit.text())
                if out_dir.exists():
                    existing_paths.append(("output", out_dir))

            # 从下拉框获取模板和 Rubric 文件路径
            template_path = self.template_combo.currentData()
            if template_path:
                template = Path(template_path)
                if template.exists():
                    existing_paths.append(("template", template))

            rubric_path = self.rubric_combo.currentData()
            if rubric_path:
                rubric = Path(rubric_path)
                if rubric.exists():
                    existing_paths.append(("rubric", rubric))

            # 创建 ZIP 文件
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 添加配置文件
                zipf.writestr("config.json", json.dumps(config_content, indent=2, ensure_ascii=False))

                # 添加其他文件和目录
                for name, path in existing_paths:
                    if path.is_file():
                        zipf.write(path, f"{name}/{path.name}")
                    elif path.is_dir():
                        for item in path.rglob('*'):
                            if item.is_file():
                                arc_name = f"{name}/{item.relative_to(path)}"
                                zipf.write(item, arc_name)

            # 计算备份大小
            size_mb = backup_path.stat().st_size / (1024 * 1024)

            self.status_changed.emit(f"备份成功: {backup_path.name} ({size_mb:.1f} MB)")

        except Exception as e:
            self.status_changed.emit(f"备份失败: {str(e)}")
