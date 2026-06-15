"""
主窗口模块

提供应用的主窗口界面，包含导航菜单和内容区域
"""

from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QListWidget, QListWidgetItem, QSplitter,
    QLabel, QPushButton, QStatusBar, QMessageBox, QFileDialog,
    QToolBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction

from app.models.domain import ProjectConfig
from app.config.settings import ConfigManager

# 导入所有视图
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.plagiarism_view import PlagiarismView
from app.ui.views.grading_view import GradingView
from app.ui.views.feedback_view import FeedbackView
from app.ui.views.report_view import ReportView
from app.ui.views.settings_view import SettingsView
from app.ui.views.multi_class_view import MultiClassView
from app.ui.about_dialog import AboutDialog
from app.ui.file_dialog_utils import get_open_filename


class MainWindow(QMainWindow):
    """主窗口"""

    # 信号
    project_loaded = pyqtSignal(object)  # 项目配置加载成功
    project_closed = pyqtSignal()  # 项目关闭
    status_changed = pyqtSignal(str)  # 状态更新

    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.current_project: ProjectConfig = None
        self.selected_classes: List = []  # 存储Dashboard选中的班级列表

        # 视图引用
        self.views = {}
        self.dashboard_view = None
        self.plagiarism_view = None
        self.grading_view = None
        self.feedback_view = None
        self.report_view = None
        self.settings_view = None
        self.multi_class_view = None

        self._init_ui()
        self._create_and_register_views()
        self._connect_view_signals()
        self._load_recent_projects()

    def _init_ui(self):
        """初始化UI"""
        self.setWindowTitle("STM32教学管理系统")
        self.setMinimumSize(1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧导航面板
        self._create_navigation_panel(splitter)

        # 右侧内容区域
        self._create_content_area(splitter)

        # 设置分割比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1000])

        main_layout.addWidget(splitter)

        # 创建状态栏
        self._create_status_bar()

        # 创建工具栏
        self._create_toolbar()

    def _create_navigation_panel(self, parent):
        """创建导航面板"""
        nav_panel = QWidget()
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        # 应用标题
        title_label = QLabel("STM32教学管理")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                padding: 20px 10px 10px 10px;
                color: #2c3e50;
            }
        """)
        nav_layout.addWidget(title_label)

        # 导航列表
        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-bottom: 1px solid #e9ecef;
            }
            QListWidget::item:hover {
                background-color: #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # 添加导航项
        nav_items = [
            ("overview", "📊 概览"),
            ("multi_class", "🔍 查重检测"),
            ("grading", "📝 评分评估"),
            ("feedback", "💬 反馈生成"),
            ("reports", "📄 报告输出"),
            ("settings", "⚙️ 设置"),
        ]

        for item_id, item_text in nav_items:
            list_item = QListWidgetItem(item_text)
            list_item.setData(Qt.ItemDataRole.UserRole, item_id)
            self.nav_list.addItem(list_item)

        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        nav_layout.addWidget(self.nav_list)

        # 最近项目标题
        recent_label = QLabel("最近项目")
        recent_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                padding: 20px 10px 5px 10px;
                color: #6c757d;
            }
        """)
        nav_layout.addWidget(recent_label)

        # 最近项目列表
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(200)
        self.recent_list.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 8px 15px;
                font-size: 11px;
            }
            QListWidget::item:hover {
                background-color: #e9ecef;
            }
        """)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_project_clicked)
        nav_layout.addWidget(self.recent_list)

        nav_layout.addStretch()

        parent.addWidget(nav_panel)

    def _create_content_area(self, parent):
        """创建内容区域"""
        # 堆叠窗口用于切换不同视图
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background-color: white;
            }
        """)

        # 占位视图 - 稍后会替换为实际视图
        placeholder = self._create_placeholder_view("概览")
        self.content_stack.addWidget(placeholder)
        self.views['overview'] = placeholder

        placeholder = self._create_placeholder_view("多班级处理")
        self.content_stack.addWidget(placeholder)
        self.views['multi_class'] = placeholder

        placeholder = self._create_placeholder_view("评分评估")
        self.content_stack.addWidget(placeholder)
        self.views['grading'] = placeholder

        placeholder = self._create_placeholder_view("反馈生成")
        self.content_stack.addWidget(placeholder)
        self.views['feedback'] = placeholder

        placeholder = self._create_placeholder_view("报告输出")
        self.content_stack.addWidget(placeholder)
        self.views['reports'] = placeholder

        placeholder = self._create_placeholder_view("设置")
        self.content_stack.addWidget(placeholder)
        self.views['settings'] = placeholder

        parent.addWidget(self.content_stack)

    def _create_placeholder_view(self, title: str) -> QWidget:
        """创建占位视图"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        label = QLabel(f"{title} - 功能开发中...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                color: #adb5bd;
                padding: 100px;
            }
        """)

        layout.addWidget(label)
        return widget

    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                border-top: 1px solid #dee2e6;
                color: #495057;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                spacing: 5px;
                padding: 5px;
            }
            QToolBar QToolButton {
                padding: 5px 10px;
            }
        """)

        # 新建项目（快速开始）
        new_action = QAction("🚀 快速开始", self)
        new_action.triggered.connect(self._on_new_project)
        toolbar.addAction(new_action)

        # 设置
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(lambda: self._navigate_to_view("settings"))
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        # 刷新
        refresh_action = QAction("🔄 刷新", self)
        refresh_action.triggered.connect(self._on_refresh)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # 关于
        about_action = QAction("ℹ️ 关于", self)
        about_action.triggered.connect(self._on_about)
        toolbar.addAction(about_action)

        self.addToolBar(toolbar)

    def _on_nav_changed(self, current_row: int):
        """导航项变化"""
        item = self.nav_list.item(current_row)
        if item:
            view_id = item.data(Qt.ItemDataRole.UserRole)
            if view_id in self.views:
                self.content_stack.setCurrentWidget(self.views[view_id])

    def _on_new_project(self):
        """新建项目"""
        self.show_status("创建新项目...")

        # 使用默认配置
        config = self.config_manager.create_default_config()
        self.current_project = config

        # 通知所有视图
        self._on_config_changed(config)

        self.project_loaded.emit(config)
        self.show_status(f"新项目已创建: {config.class_name}")
        # 自动导航到设置页面
        self._navigate_to_view("settings")

    def _on_refresh(self):
        """刷新"""
        self._load_recent_projects()
        self.show_status("已刷新")

    def _on_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self)
        dialog.exec()

    def _on_recent_project_clicked(self, item):
        """最近项目项点击"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self._load_project(Path(file_path))

    def _load_project(self, project_path):
        """加载项目"""
        config = self.config_manager.load_project(project_path)
        if config:
            self.current_project = config
            self._on_config_changed(config)  # 通知所有视图
            self.project_loaded.emit(config)
            self.show_status(f"项目已加载: {config.class_name}")
        else:
            QMessageBox.warning(self, "错误", "加载项目失败")

    def _load_recent_projects(self):
        """加载最近项目列表"""
        self.recent_list.clear()

        recent = self.config_manager.get_recent_projects()
        for project in recent[:5]:  # 最多显示5个
            item = QListWidgetItem(f"📁 {project['name']}")
            item.setData(Qt.ItemDataRole.UserRole, project['path'])
            item.setToolTip(project['path'])
            self.recent_list.addItem(item)

    def show_status(self, message: str):
        """显示状态消息"""
        self.status_bar.showMessage(message, 5000)  # 显示5秒
        self.status_changed.emit(message)

    def _create_and_register_views(self):
        """创建并注册所有视图"""
        # 创建各个视图
        self.dashboard_view = DashboardView()
        self.plagiarism_view = PlagiarismView()
        self.multi_class_view = MultiClassView()
        self.grading_view = GradingView()
        self.feedback_view = FeedbackView()
        self.report_view = ReportView()
        self.settings_view = SettingsView()

        # 注册视图
        self.register_view('overview', self.dashboard_view)
        self.register_view('plagiarism', self.plagiarism_view)
        self.register_view('multi_class', self.multi_class_view)
        self.register_view('grading', self.grading_view)
        self.register_view('feedback', self.feedback_view)
        self.register_view('reports', self.report_view)
        self.register_view('settings', self.settings_view)

    def _connect_view_signals(self):
        """连接视图信号"""
        if self.dashboard_view:
            self.dashboard_view.status_changed.connect(self.show_status)
            self.dashboard_view.navigate_to.connect(self._navigate_to_view)
            self.dashboard_view.new_project.connect(self._on_new_project)
            # 新增：连接Dashboard配置信号
            self.dashboard_view.config_selected.connect(self._on_config_changed)
            self.dashboard_view.class_switched.connect(self._on_config_changed)

        if self.multi_class_view:
            self.multi_class_view.status_changed.connect(self.show_status)

        if self.plagiarism_view:
            self.plagiarism_view.status_changed.connect(self.show_status)

        if self.grading_view:
            self.grading_view.status_changed.connect(self.show_status)

        if self.feedback_view:
            self.feedback_view.status_changed.connect(self.show_status)

        if self.report_view:
            self.report_view.status_changed.connect(self.show_status)

        if self.settings_view:
            self.settings_view.config_changed.connect(self._on_config_changed)
            self.settings_view.status_changed.connect(self.show_status)

    def _navigate_to_view(self, view_id: str):
        """导航到指定视图"""
        # 找到对应的导航项
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == view_id:
                self.nav_list.setCurrentRow(i)
                break

    def _on_config_changed(self, config: ProjectConfig):
        """配置变化处理"""
        self.current_project = config

        # 从Dashboard获取选中的班级列表（如果有）
        if self.dashboard_view and hasattr(self.dashboard_view, 'selected_classes'):
            self.selected_classes = self.dashboard_view.selected_classes

        # 通知所有视图配置已变化
        if self.plagiarism_view:
            self.plagiarism_view.set_config(config)
        if self.grading_view:
            self.grading_view.set_config(config)
        if self.feedback_view:
            self.feedback_view.set_config(config)
        if self.report_view:
            self.report_view.set_config(config)
        if self.settings_view:
            self.settings_view.set_config(config)
        if self.dashboard_view:
            self.dashboard_view.set_config(config)
        if self.multi_class_view:
            self.multi_class_view.set_config(config)
            # 如果有选中的多个班级，也传递给MultiClassView
            if len(self.selected_classes) > 1:
                self.multi_class_view.set_dashboard_classes(self.selected_classes)

    def register_view(self, view_id: str, widget):
        """注册视图"""
        if view_id in self.views:
            # 替换现有视图
            current_index = self.content_stack.indexOf(self.views[view_id])
            if current_index >= 0:
                self.content_stack.removeWidget(self.views[view_id])
                self.content_stack.insertWidget(current_index, widget)
            else:
                self.content_stack.addWidget(widget)

            self.views[view_id] = widget
        else:
            # 添加新视图
            self.content_stack.addWidget(widget)
            self.views[view_id] = widget
