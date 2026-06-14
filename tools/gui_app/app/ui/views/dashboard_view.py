"""
概览仪表盘视图

提供项目概览和快捷操作的界面
"""

from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QGroupBox, QFrame,
    QScrollArea, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from app.models.domain import ProjectConfig


class DashboardView(QWidget):
    """概览仪表盘视图"""

    # 信号
    status_changed = pyqtSignal(str)
    navigate_to = pyqtSignal(str)  # 导航到指定视图
    new_project = pyqtSignal()

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

        # 欢迎区域
        welcome_group = self._create_welcome_section()
        content_layout.addWidget(welcome_group)

        # 项目信息区域
        self.project_info_group = self._create_project_info_section()
        content_layout.addWidget(self.project_info_group)

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
        """创建项目信息区域"""
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

        # 班级名称
        layout.addWidget(QLabel("班级名称:"), 0, 0)
        self.class_name_label = QLabel("未加载项目")
        self.class_name_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(self.class_name_label, 0, 1)

        # 实验类型
        layout.addWidget(QLabel("实验类型:"), 0, 2)
        self.experiment_type_label = QLabel("-")
        self.experiment_type_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(self.experiment_type_label, 0, 3)

        # 项目路径
        layout.addWidget(QLabel("项目路径:"), 1, 0)
        self.project_path_label = QLabel("-")
        self.project_path_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        self.project_path_label.setWordWrap(True)
        layout.addWidget(self.project_path_label, 1, 1, 1, 3)

        group.setLayout(layout)
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
        plagiarism_btn.clicked.connect(lambda: self.navigate_to.emit("plagiarism"))

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
        grading_btn.clicked.connect(lambda: self.navigate_to.emit("grading"))

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
        # TODO: 加载项目
        self.status_changed.emit(f"正在加载项目: {item.text()}")

    def set_config(self, config: ProjectConfig):
        """设置配置"""
        self.current_config = config

        # 更新项目信息
        self.class_name_label.setText(config.class_name)
        self.experiment_type_label.setText(config.experiment_type.value)
        self.project_path_label.setText(str(config.experiment_dir))

        # 更新提交数量
        # TODO: 从实际数据获取
        self.submission_count_label.setText("0")

    def update_plagiarism_status(self, status: str, count: int = 0):
        """更新查重状态"""
        self.plagiarism_status_label.setText(status)

    def update_grading_status(self, status: str, count: int = 0):
        """更新评分状态"""
        self.grading_status_label.setText(status)

    def update_feedback_count(self, count: int):
        """更新反馈数量"""
        self.feedback_count_label.setText(str(count))
