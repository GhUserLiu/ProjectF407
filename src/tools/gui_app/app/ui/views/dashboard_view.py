"""
概览仪表盘视图

提供项目概览和快捷操作的界面
整合统一配置入口，替代各功能视图的分散路径选择
"""

from pathlib import Path
from typing import Optional, List, Dict
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QGroupBox, QFrame,
    QScrollArea, QProgressBar, QListWidget, QListWidgetItem,
    QComboBox, QLineEdit, QSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont

from app.models.domain import ProjectConfig, ExperimentType
from app.ui.file_dialog_utils import get_existing_directory

# 导入多班级服务
try:
    from app.core.multi_class_service import MultiClassService
    MULTI_CLASS_AVAILABLE = True
except ImportError:
    MULTI_CLASS_AVAILABLE = False
    print("[WARNING] MultiClassService not available", file=sys.stderr)


class DashboardView(QWidget):
    """概览仪表盘视图"""

    # 信号
    status_changed = pyqtSignal(str)
    navigate_to = pyqtSignal(str)  # 导航到指定视图
    new_project = pyqtSignal()
    config_selected = pyqtSignal(object)  # 配置确认信号
    class_switched = pyqtSignal(object)  # 班级切换信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None

        # 配置相关属性
        self.teaching_base_path: Optional[Path] = None
        self.selected_semester: str = "2026-春季"
        self.selected_experiment: str = "07-car-gear"
        self.class_pattern: str = "*班"
        self.discovered_classes: List[Dict] = []
        self.selected_classes: List[Dict] = []

        # 多班级服务
        self.multi_class_service = None
        if MULTI_CLASS_AVAILABLE:
            try:
                self.multi_class_service = MultiClassService()
            except Exception as e:
                print(f"[WARNING] Failed to initialize MultiClassService: {e}", file=sys.stderr)

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

        # 欢迎区域
        welcome_group = self._create_welcome_section()
        content_layout.addWidget(welcome_group)

        # 项目信息区域（包含班级切换器）
        self.project_info_group = self._create_project_info_section()
        content_layout.addWidget(self.project_info_group)

        # 配置选择区域（新增）
        config_group = self._create_config_section()
        content_layout.addWidget(config_group)

        # 快捷操作区域
        quick_actions_group = self._create_quick_actions_section()
        content_layout.addWidget(quick_actions_group)

        # 状态概览区域
        self.status_overview_group = self._create_status_overview_section()
        content_layout.addWidget(self.status_overview_group)

        # 最近项目区域
        recent_group = self._create_recent_projects_section()
        content_layout.addWidget(recent_group)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_welcome_section(self) -> QGroupBox:
        """创建欢迎区域"""
        group = QGroupBox()
        group.setStyleSheet("""
            QGroupBox {
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0.5,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 12px;
                padding: 20px;
            }
        """)

        layout = QVBoxLayout()

        title = QLabel("欢迎使用 STM32教学管理系统")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)

        subtitle = QLabel("集成查重检测、评分评估、反馈生成的一站式教学工具")
        subtitle.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.9);
                font-size: 14px;
                margin-top: 5px;
            }
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        group.setLayout(layout)
        return group

    def _create_project_info_section(self) -> QGroupBox:
        """创建项目信息区域（包含班级切换器）"""
        group = QGroupBox("当前项目")
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

        layout = QGridLayout()

        # 班级切换器行
        layout.addWidget(QLabel("当前班级:"), 0, 0)
        self.class_switcher_combo = QComboBox()
        self.class_switcher_combo.setMinimumWidth(200)
        self.class_switcher_combo.currentIndexChanged.connect(self._on_class_switched)
        self.class_switcher_combo.setEnabled(False)
        layout.addWidget(self.class_switcher_combo, 0, 1)

        # 实验类型
        layout.addWidget(QLabel("实验类型:"), 0, 2)
        self.experiment_type_label = QLabel("-")
        self.experiment_type_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(self.experiment_type_label, 0, 3)

        # 项目路径
        layout.addWidget(QLabel("项目路径:"), 1, 0)
        self.project_path_label = QLabel("请在下方选择作业目录")
        self.project_path_label.setStyleSheet("color: #dc3545; font-size: 11px;")
        self.project_path_label.setWordWrap(True)
        layout.addWidget(self.project_path_label, 1, 1, 1, 3)

        group.setLayout(layout)
        return group

    def _create_config_section(self) -> QGroupBox:
        """创建配置选择区域"""
        group = QGroupBox("选择作业目录")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #f8f9fa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 15px;
                padding: 0 5px;
                color: #3498db;
            }
        """)

        main_layout = QVBoxLayout()

        # 教学目录选择行
        dir_layout = QHBoxLayout()
        dir_label = QLabel("教学目录:")
        dir_label.setMinimumWidth(80)

        self.base_path_label = QLabel("未选择")
        self.base_path_label.setStyleSheet("color: #6c757d; padding: 5px;")
        self.base_path_label.setWordWrap(True)

        select_dir_btn = QPushButton("📂 选择教学目录")
        select_dir_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        select_dir_btn.clicked.connect(self._on_select_teaching_directory)

        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.base_path_label, 1)
        dir_layout.addWidget(select_dir_btn)
        main_layout.addLayout(dir_layout)

        # 学期和实验选择行
        selection_layout = QGridLayout()

        # 学期选择
        selection_layout.addWidget(QLabel("学期:"), 0, 0)
        self.semester_combo = QComboBox()
        self.semester_combo.addItem("2026-春季", "2026-春季")
        self.semester_combo.addItem("2025-秋季", "2025-秋季")
        self.semester_combo.addItem("2025-春季", "2025-春季")
        self.semester_combo.currentIndexChanged.connect(
            lambda i: setattr(self, 'selected_semester', self.semester_combo.itemData(i))
        )
        selection_layout.addWidget(self.semester_combo, 0, 1)

        # 实验选择
        selection_layout.addWidget(QLabel("实验:"), 0, 2)
        self.experiment_combo = QComboBox()
        self.experiment_combo.addItem("07-car-gear (档位实验)", "07-car-gear")
        self.experiment_combo.addItem("01-turn-signal (转向灯)", "01-turn-signal")
        self.experiment_combo.addItem("02-pwm-led (PWM LED)", "02-pwm-led")
        self.experiment_combo.currentIndexChanged.connect(
            lambda i: setattr(self, 'selected_experiment', self.experiment_combo.itemData(i))
        )
        selection_layout.addWidget(self.experiment_combo, 0, 3)

        # 班级模式
        selection_layout.addWidget(QLabel("班级模式:"), 1, 0)
        self.class_pattern_input = QLineEdit("*班")
        self.class_pattern_input.textChanged.connect(
            lambda t: setattr(self, 'class_pattern', t or "*班")
        )
        selection_layout.addWidget(self.class_pattern_input, 1, 1)

        # 发现班级按钮
        self.discover_btn = QPushButton("🔍 发现班级")
        self.discover_btn.setEnabled(False)
        self.discover_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.discover_btn.clicked.connect(self._on_discover_classes)
        selection_layout.addWidget(self.discover_btn, 1, 2, 1, 2)

        main_layout.addLayout(selection_layout)

        # 班级列表区域
        class_list_layout = QVBoxLayout()
        class_list_label = QLabel("发现的班级:")
        class_list_layout.addWidget(class_list_label)

        self.class_list = QListWidget()
        self.class_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: white;
                min-height: 100px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:checked {
                background-color: #d4edda;
                color: #155724;
            }
        """)
        self.class_list.itemChanged.connect(self._on_class_selection_changed)
        class_list_layout.addWidget(self.class_list)

        # 班级列表提示
        self.class_list_hint = QLabel("💡 提示：勾选班级后点击确认配置")
        self.class_list_hint.setStyleSheet("color: #6c757d; font-size: 11px; padding: 5px;")
        self.class_list_hint.setVisible(False)
        class_list_layout.addWidget(self.class_list_hint)

        main_layout.addLayout(class_list_layout)

        # 确认配置按钮
        confirm_layout = QHBoxLayout()
        confirm_layout.addStretch()

        self.confirm_config_btn = QPushButton("✅ 确认配置")
        self.confirm_config_btn.setEnabled(False)
        self.confirm_config_btn.setStyleSheet("""
            QPushButton {
                padding: 10px 30px;
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
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.confirm_config_btn.clicked.connect(self._on_confirm_config)
        confirm_layout.addWidget(self.confirm_config_btn)
        confirm_layout.addStretch()

        main_layout.addLayout(confirm_layout)

        group.setLayout(main_layout)
        return group

    def _create_quick_actions_section(self) -> QGroupBox:
        """创建快捷操作区域"""
        group = QGroupBox("快捷操作")
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

        layout = QGridLayout()

        # 快速开始（新建项目）
        new_project_btn = QPushButton("🚀 快速开始")
        new_project_btn.setStyleSheet("""
            QPushButton {
                padding: 15px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_project_btn.clicked.connect(self.new_project.emit)

        # 打开设置
        settings_btn = QPushButton("⚙️ 打开设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                padding: 15px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        settings_btn.clicked.connect(lambda: self.navigate_to.emit("settings"))

        # 开始查重
        plagiarism_btn = QPushButton("🔍 开始查重")
        plagiarism_btn.setStyleSheet("""
            QPushButton {
                padding: 15px;
                background-color: #fd7e14;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        plagiarism_btn.clicked.connect(lambda: self._check_config_before_action("plagiarism"))

        # 开始评分
        grading_btn = QPushButton("📝 开始评分")
        grading_btn.setStyleSheet("""
            QPushButton {
                padding: 15px;
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        grading_btn.clicked.connect(lambda: self._check_config_before_action("grading"))

        layout.addWidget(new_project_btn, 0, 0)
        layout.addWidget(settings_btn, 0, 1)
        layout.addWidget(plagiarism_btn, 1, 0)
        layout.addWidget(grading_btn, 1, 1)

        group.setLayout(layout)
        return group

    def _create_status_overview_section(self) -> QGroupBox:
        """创建状态概览区域"""
        group = QGroupBox("处理状态")
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

        layout = QGridLayout()

        # 提交状态
        submission_frame = QFrame()
        submission_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        submission_layout = QVBoxLayout(submission_frame)

        self.submission_count_label = QLabel("0")
        self.submission_count_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #3498db;
            }
        """)
        self.submission_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        submission_label = QLabel("已提交")
        submission_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        submission_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        submission_layout.addWidget(self.submission_count_label)
        submission_layout.addWidget(submission_label)

        # 查重状态
        plagiarism_frame = QFrame()
        plagiarism_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        plagiarism_layout = QVBoxLayout(plagiarism_frame)

        self.plagiarism_status_label = QLabel("未开始")
        self.plagiarism_status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #6c757d;
            }
        """)
        self.plagiarism_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        plagiarism_label = QLabel("查重检测")
        plagiarism_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        plagiarism_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        plagiarism_layout.addWidget(self.plagiarism_status_label)
        plagiarism_layout.addWidget(plagiarism_label)

        # 评分状态
        grading_frame = QFrame()
        grading_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        grading_layout = QVBoxLayout(grading_frame)

        self.grading_status_label = QLabel("未开始")
        self.grading_status_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #6c757d;
            }
        """)
        self.grading_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grading_label = QLabel("评分评估")
        grading_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        grading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grading_layout.addWidget(self.grading_status_label)
        grading_layout.addWidget(grading_label)

        # 反馈状态
        feedback_frame = QFrame()
        feedback_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        feedback_layout = QVBoxLayout(feedback_frame)

        self.feedback_count_label = QLabel("0")
        self.feedback_count_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #28a745;
            }
        """)
        self.feedback_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        feedback_label = QLabel("已生成反馈")
        feedback_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        feedback_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        feedback_layout.addWidget(self.feedback_count_label)
        feedback_layout.addWidget(feedback_label)

        layout.addWidget(submission_frame, 0, 0)
        layout.addWidget(plagiarism_frame, 0, 1)
        layout.addWidget(grading_frame, 0, 2)
        layout.addWidget(feedback_frame, 0, 3)

        group.setLayout(layout)
        return group

    def _create_recent_projects_section(self) -> QGroupBox:
        """创建最近项目区域"""
        group = QGroupBox("最近项目")
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

        layout = QVBoxLayout()

        self.recent_list = QListWidget()
        self.recent_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 5px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #e9ecef;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_project_clicked)

        # 添加占位项目
        self._add_placeholder_items()

        layout.addWidget(self.recent_list)

        group.setLayout(layout)
        return group

    def _add_placeholder_items(self):
        """添加占位项目"""
        placeholder_items = [
            "📁 汽服2302B班 - 档位实验 (2小时前)",
            "📁 汽服2302B班 - 转向灯实验 (昨天)",
            "📁 汽服2302B班 - PWM实验 (3天前)"
        ]

        for item_text in placeholder_items:
            item = QListWidgetItem(item_text)
            self.recent_list.addItem(item)

    def _on_recent_project_clicked(self, item):
        """最近项目点击"""
        self.status_changed.emit(f"正在加载项目: {item.text()}")

    # ==================== 配置相关方法 ====================

    def _on_select_teaching_directory(self):
        """选择教学目录"""
        dir_path = get_existing_directory(
            self, "选择教学基础目录", 'submission', None
        )

        if dir_path:
            self.teaching_base_path = Path(dir_path)
            self.base_path_label.setText(str(self.teaching_base_path))
            self.discover_btn.setEnabled(True)
            self.status_changed.emit(f"已选择教学目录: {dir_path}")

    def _on_discover_classes(self):
        """发现班级"""
        if not self.teaching_base_path:
            self.status_changed.emit("请先选择教学目录")
            return

        if not self.multi_class_service:
            self.status_changed.emit("多班级服务不可用")
            return

        self.status_changed.emit("正在扫描班级...")
        self.discover_btn.setEnabled(False)

        try:
            classes = self.multi_class_service.discover_classes(
                base_dir=self.teaching_base_path,
                semester=self.selected_semester,
                experiment=self.selected_experiment,
                class_pattern=self.class_pattern
            )

            self.discovered_classes = classes
            self._display_classes(classes)

            if classes:
                self.status_changed.emit(f"发现 {len(classes)} 个班级")
                self.class_list_hint.setVisible(True)
            else:
                self.status_changed.emit("未发现任何班级，请检查路径和配置")
                self.class_list_hint.setText("⚠️ 未发现班级，请检查路径和配置")
                self.class_list_hint.setVisible(True)

        except Exception as e:
            self.status_changed.emit(f"发现班级失败: {str(e)}")
            self.class_list_hint.setText(f"⚠️ 错误: {str(e)}")
            self.class_list_hint.setVisible(True)
        finally:
            self.discover_btn.setEnabled(True)

    def _display_classes(self, classes: List[Dict]):
        """显示发现的班级"""
        self.class_list.clear()
        self.selected_classes = []

        for class_info in classes:
            class_name = class_info.get('class_name', '未知班级')
            student_count = class_info.get('student_count', 0)

            item = QListWidgetItem(f"📁 {class_name} ({student_count}人)")
            item.setData(Qt.ItemDataRole.UserRole, class_info)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)

            self.class_list.addItem(item)

    def _on_class_selection_changed(self, item):
        """班级选择变化"""
        self.selected_classes = []

        for i in range(self.class_list.count()):
            list_item = self.class_list.item(i)
            if list_item.checkState() == Qt.CheckState.Checked:
                class_info = list_item.data(Qt.ItemDataRole.UserRole)
                self.selected_classes.append(class_info)

        # 更新确认按钮状态
        self.confirm_config_btn.setEnabled(len(self.selected_classes) > 0)

        if self.selected_classes:
            self.class_list_hint.setText(f"✅ 已选择 {len(self.selected_classes)} 个班级")
        else:
            self.class_list_hint.setText("💡 提示：勾选班级后点击确认配置")

    def _on_confirm_config(self):
        """确认配置"""
        if not self.selected_classes:
            self.status_changed.emit("请至少选择一个班级")
            return

        try:
            # 为第一个选中的班级生成配置（默认激活）
            primary_class = self.selected_classes[0]
            config = self._create_config_for_class(primary_class)

            self.current_config = config

            # 更新班级切换器
            self._update_class_switcher()

            # 更新显示
            self._update_config_display()

            # 发送配置确认信号
            self.config_selected.emit(config)

            self.status_changed.emit(f"配置已确认: {config.class_name}")

        except Exception as e:
            QMessageBox.critical(
                self,
                "配置确认失败",
                f"无法生成配置:\n{str(e)}"
            )

    def _create_config_for_class(self, class_info: Dict) -> ProjectConfig:
        """为班级创建配置"""
        experiment_str = class_info.get('experiment', self.selected_experiment)

        # 映射实验字符串到枚举
        experiment_map = {
            "07-car-gear": ExperimentType.CAR_GEAR,
            "01-turn-signal": ExperimentType.TURN_SIGNAL,
            "02-pwm-led": ExperimentType.PWM_LED,
        }
        experiment_type = experiment_map.get(experiment_str, ExperimentType.CAR_GEAR)

        return ProjectConfig(
            class_name=class_info['class_name'],
            experiment_type=experiment_type,
            experiment_dir=Path(class_info['experiment_dir']),
            submissions_dir=Path(class_info.get('submissions_dir',
                Path(class_info['experiment_dir']) / 'submissions' / 'extracted'))
        )

    def _update_class_switcher(self):
        """更新班级切换器"""
        if not self.selected_classes:
            return

        # 保存当前选择
        current_index = self.class_switcher_combo.currentIndex()

        # 清空并重新填充
        self.class_switcher_combo.clear()
        for class_info in self.selected_classes:
            self.class_switcher_combo.addItem(
                class_info['class_name'],
                class_info
            )

        self.class_switcher_combo.setEnabled(True)

        # 恢复选择（如果可能）
        if current_index >= 0 and current_index < self.class_switcher_combo.count():
            self.class_switcher_combo.setCurrentIndex(current_index)
        else:
            self.class_switcher_combo.setCurrentIndex(0)

    def _on_class_switched(self, index):
        """班级切换处理"""
        if index < 0 or index >= self.class_switcher_combo.count():
            return

        class_info = self.class_switcher_combo.itemData(index)
        if not class_info:
            return

        try:
            config = self._create_config_for_class(class_info)
            self.current_config = config

            # 更新显示
            self._update_config_display()

            # 发送班级切换信号
            self.class_switched.emit(config)

            self.status_changed.emit(f"已切换到: {config.class_name}")

        except Exception as e:
            self.status_changed.emit(f"切换班级失败: {str(e)}")

    def _update_config_display(self):
        """更新配置显示"""
        if not self.current_config:
            return

        # 更新项目信息
        self.experiment_type_label.setText(self.current_config.experiment_type.value)
        self.project_path_label.setText(str(self.current_config.experiment_dir))
        self.project_path_label.setStyleSheet("color: #28a745; font-size: 11px;")

        # TODO: 更新提交数量
        # self.submission_count_label.setText("0")

    def _check_config_before_action(self, action: str):
        """执行操作前检查配置"""
        if not self.current_config:
            QMessageBox.warning(
                self,
                "未配置",
                "请先在上方选择作业目录并确认配置后再执行此操作。"
            )
            return

        # 配置已就绪，导航到对应视图
        self.navigate_to.emit(action)

    # ==================== 公共方法 ====================

    def set_config(self, config: ProjectConfig):
        """设置配置（从外部加载）"""
        self.current_config = config

        # 更新班级切换器
        if config.class_name:
            self.class_switcher_combo.clear()
            self.class_switcher_combo.addItem(config.class_name, config)
            self.class_switcher_combo.setEnabled(True)

        # 更新显示
        self._update_config_display()

    def update_plagiarism_status(self, status: str, count: int = 0):
        """更新查重状态"""
        self.plagiarism_status_label.setText(status)

    def update_grading_status(self, status: str, count: int = 0):
        """更新评分状态"""
        self.grading_status_label.setText(status)

    def update_feedback_count(self, count: int):
        """更新反馈数量"""
        self.feedback_count_label.setText(str(count))
