#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主窗口
Main Window

自动化批阅系统的主界面，包含：
- 配置面板
- 进度显示
- 结果表格
- 菜单栏和工具栏
"""

import sys
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton, QLineEdit,
    QComboBox, QCheckBox, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QProgressBar,
    QTextEdit, QSplitter, QTabWidget, QMessageBox,
    QStatusBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont

# 导入批阅模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from tools.auto_grading import AutoGradingFacade, AutoGradingConfig
from tools.auto_grading.facade import PipelineResult
from tools.auto_grading_gui.workers.grading_worker import GradingWorker


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.config = AutoGradingConfig()
        self.facade = AutoGradingFacade(self.config)
        self.current_result = None
        self.is_grading = False
        self.grading_worker = None

        self.setup_ui()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("自动化批阅系统 v1.0")
        self.setMinimumSize(1000, 700)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建中央窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 1. 配置面板
        config_group = self.create_config_panel()
        main_layout.addWidget(config_group)

        # 2. 进度显示
        progress_group = self.create_progress_panel()
        main_layout.addWidget(progress_group)

        # 3. 结果显示（使用分割器）
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 3.1 统计信息
        stats_group = self.create_stats_panel()
        splitter.addWidget(stats_group)

        # 3.2 学生列表
        results_group = self.create_results_panel()
        splitter.addWidget(results_group)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter, 1)

        # 4. 日志输出
        log_group = self.create_log_panel()
        main_layout.addWidget(log_group)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def create_menu_bar(self):
        """创建菜单栏"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        open_action = QAction("打开压缩包(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_zip_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 工具菜单
        tools_menu = menubar.addMenu("工具(&T)")

        export_action = QAction("导出班级报告(&E)", self)
        export_action.triggered.connect(self.export_class_report)
        tools_menu.addAction(export_action)

        export_all_action = QAction("导出所有个人报告(&A)", self)
        export_all_action.triggered.connect(self.export_all_reports)
        tools_menu.addAction(export_all_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_config_panel(self):
        """创建配置面板"""
        group = QGroupBox("批阅配置")
        layout = QVBoxLayout()

        # 班级压缩包
        zip_layout = QHBoxLayout()
        zip_layout.addWidget(QLabel("班级压缩包:"))
        self.zip_path_edit = QLineEdit()
        self.zip_path_edit.setPlaceholderText("选择班级压缩包...")
        self.zip_path_edit.setReadOnly(True)
        zip_layout.addWidget(self.zip_path_edit)

        select_btn = QPushButton("选择文件...")
        select_btn.clicked.connect(self.select_zip_file)
        zip_layout.addWidget(select_btn)

        layout.addLayout(zip_layout)

        # 参数配置
        params_layout = QHBoxLayout()

        # 班级名称
        class_layout = QVBoxLayout()
        class_layout.addWidget(QLabel("班级名称:"))
        self.class_name_edit = QLineEdit()
        self.class_name_edit.setPlaceholderText("例如：汽服2302B班")
        class_layout.addWidget(self.class_name_edit)
        params_layout.addLayout(class_layout)

        # 实验ID
        exp_layout = QVBoxLayout()
        exp_layout.addWidget(QLabel("实验ID:"))
        self.experiment_id_edit = QLineEdit()
        self.experiment_id_edit.setPlaceholderText("例如：07-car-gear")
        exp_layout.addWidget(self.experiment_id_edit)
        params_layout.addLayout(exp_layout)

        # 评分标准
        rubric_layout = QVBoxLayout()
        rubric_layout.addWidget(QLabel("评分标准:"))
        self.rubric_combo = QComboBox()
        self.rubric_combo.addItem("默认 (data/rubrics/rubric.json)")
        rubric_layout.addWidget(self.rubric_combo)
        params_layout.addLayout(rubric_layout)

        layout.addLayout(params_layout)

        # 选项
        options_layout = QHBoxLayout()
        self.check_organize = QCheckBox("整理提交格式")
        self.check_organize.setChecked(True)
        self.check_compile = QCheckBox("编译检查")
        self.check_compile.setChecked(True)
        self.check_analyze = QCheckBox("代码分析")
        self.check_analyze.setChecked(True)
        self.check_grade = QCheckBox("报告评分")
        self.check_grade.setChecked(True)

        options_layout.addWidget(self.check_organize)
        options_layout.addWidget(self.check_compile)
        options_layout.addWidget(self.check_analyze)
        options_layout.addWidget(self.check_grade)

        layout.addLayout(options_layout)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_btn = QPushButton("开始批阅")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_btn.clicked.connect(self.start_grading)
        button_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_grading)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()

        layout.addLayout(button_layout)
        group.setLayout(layout)

        return group

    def create_progress_panel(self):
        """创建进度面板"""
        group = QGroupBox("批阅进度")
        layout = QVBoxLayout()

        # 创建进度条
        self.progress_bars = {}

        stages = [
            ("organize", "整理提交"),
            ("compile", "编译检查"),
            ("analyze", "代码分析"),
            ("grade", "报告评分")
        ]

        for stage_id, stage_name in stages:
            stage_layout = QHBoxLayout()
            stage_layout.addWidget(QLabel(f"{stage_name}:"), 1)

            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            progress_bar.setFormat("%p% (%v/%m)")
            progress_bar.setValue(0)

            stage_layout.addWidget(progress_bar, 3)

            self.progress_bars[stage_id] = progress_bar

            layout.addLayout(stage_layout)

        group.setLayout(layout)
        return group

    def create_stats_panel(self):
        """创建统计面板"""
        group = QGroupBox("批阅结果")
        layout = QHBoxLayout()

        # 统计标签
        stats_layout = QVBoxLayout()

        self.total_label = QLabel("总提交: 0")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.total_label)

        self.avg_label = QLabel("平均分: 0.0")
        self.avg_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.avg_label)

        self.time_label = QLabel("用时: 0:00")
        self.time_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.time_label)

        stats_layout.addStretch()

        layout.addLayout(stats_layout, 1)

        # 按钮
        buttons_layout = QVBoxLayout()

        view_report_btn = QPushButton("查看班级报告")
        view_report_btn.clicked.connect(self.view_class_report)
        buttons_layout.addWidget(view_report_btn)

        export_btn = QPushButton("导出个人报告")
        export_btn.clicked.connect(self.export_all_reports)
        buttons_layout.addWidget(export_btn)

        buttons_layout.addStretch()

        layout.addLayout(buttons_layout, 1)

        group.setLayout(layout)
        return group

    def create_results_panel(self):
        """创建结果表格"""
        group = QGroupBox("学生列表")
        layout = QVBoxLayout()

        # 创建表格
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "学号", "姓名", "编译", "代码", "报告", "总分", "等级"
        ])

        # 设置表格属性
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.doubleClicked.connect(self.show_student_detail)

        layout.addWidget(self.results_table)

        group.setLayout(layout)
        return group

    def create_log_panel(self):
        """创建日志面板"""
        group = QGroupBox("日志输出")
        group.setMaximumHeight(150)
        layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))

        layout.addWidget(self.log_text)

        group.setLayout(layout)
        return group

    def select_zip_file(self):
        """选择压缩包文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择班级压缩包",
            "",
            "ZIP文件 (*.zip)"
        )

        if file_path:
            self.zip_path_edit.setText(file_path)

            # 尝试从文件名提取信息
            file_name = Path(file_path).stem
            parts = file_name.split('-')

            if len(parts) >= 2:
                # 可能是 "班级-实验ID" 格式
                if len(parts) >= 2:
                    self.class_name_edit.setText(parts[0])
                    self.experiment_id_edit.setText(parts[1])

    def log(self, message):
        """输出日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

    def start_grading(self):
        """开始批阅"""
        # 验证输入
        zip_path = self.zip_path_edit.text()
        if not zip_path:
            QMessageBox.warning(self, "警告", "请选择班级压缩包")
            return

        class_name = self.class_name_edit.text().strip()
        if not class_name:
            QMessageBox.warning(self, "警告", "请输入班级名称")
            return

        experiment_id = self.experiment_id_edit.text().strip()
        if not experiment_id:
            QMessageBox.warning(self, "警告", "请输入实验ID")
            return

        # 禁用按钮
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.is_grading = True

        # 清空日志
        self.log_text.clear()
        self.log("开始批阅...")
        self.log(f"班级: {class_name}")
        self.log(f"实验: {experiment_id}")
        self.log(f"压缩包: {zip_path}")

        # 重置进度条
        for progress_bar in self.progress_bars.values():
            progress_bar.setValue(0)
            progress_bar.setRange(0, 100)

        # 记录开始时间
        self.start_time = datetime.now()

        # 创建并启动工作线程
        skip_org = not self.check_organize.isChecked()

        self.grading_worker = GradingWorker(
            zip_path=Path(zip_path),
            class_name=class_name,
            experiment_id=experiment_id,
            config=self.config,
            skip_organization=skip_org
        )

        # 连接信号
        self.grading_worker.stage_started.connect(self.on_stage_started)
        self.grading_worker.stage_progress.connect(self.on_stage_progress)
        self.grading_worker.stage_completed.connect(self.on_stage_completed)
        self.grading_worker.log_message.connect(self.log)
        self.grading_worker.grading_completed.connect(self.on_grading_completed)
        self.grading_worker.grading_failed.connect(self.on_grading_failed)

        # 启动线程
        self.grading_worker.start()

    def on_stage_started(self, stage_id: str, stage_name: str):
        """阶段开始"""
        if stage_id in self.progress_bars:
            progress_bar = self.progress_bars[stage_id]
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)

    def on_stage_progress(self, stage_id: str, current: int, total: int):
        """阶段进度更新"""
        if stage_id in self.progress_bars:
            progress_bar = self.progress_bars[stage_id]
            progress_bar.setRange(0, total)
            progress_bar.setValue(current)

    def on_stage_completed(self, stage_id: str):
        """阶段完成"""
        if stage_id in self.progress_bars:
            progress_bar = self.progress_bars[stage_id]
            progress_bar.setValue(progress_bar.maximum())

    def on_grading_completed(self, result: PipelineResult):
        """批阅完成"""
        self.current_result = result
        self.grading_complete()

    def on_grading_failed(self, error_message: str):
        """批阅失败"""
        self.is_grading = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        self.log(f"批阅失败: {error_message}")

        QMessageBox.critical(self, "错误", f"批阅失败:\n{error_message}")

    def cancel_grading(self):
        """取消批阅"""
        if self.is_grading:
            reply = QMessageBox.question(
                self,
                "确认",
                "确定要取消批阅吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.is_grading = False

                if self.grading_worker:
                    self.grading_worker.cancel()

                self.log("批阅已取消")

                # 等待线程结束
                if self.grading_worker and self.grading_worker.isRunning():
                    self.grading_worker.wait(3000)  # 等待最多3秒

                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)

    def grading_complete(self):
        """批阅完成"""
        self.is_grading = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        # 计算用时
        elapsed = (datetime.now() - self.start_time).total_seconds()
        minutes = int(elapsed // 60)
        seconds = int(elapsed % 60)

        # 更新统计（使用真实结果）
        if self.current_result:
            total = self.current_result.total_submissions
            avg_score = 0

            if self.current_result.grading_results:
                avg_score = sum(r.total_score for r in self.current_result.grading_results) / len(self.current_result.grading_results)

            self.total_label.setText(f"总提交: {total}")
            self.avg_label.setText(f"平均分: {avg_score:.1f}")

        self.time_label.setText(f"用时: {minutes}:{seconds:02d}")

        # 填充表格（使用真实结果）
        self.fill_results_table()

        self.log("批阅完成！")

    def fill_results_table(self, results=None):
        """填充结果表格"""
        # 使用真实结果
        if results is None and self.current_result:
            results = self.current_result.grading_results

        if not results:
            return

        # 提取数据
        table_data = []
        for result in results:
            # 提取各项得分
            compilation_score = 0
            code_score = 0
            report_score = 0
            compilation_ok = True

            for cat_score in result.category_scores:
                if cat_score.category_id == "compilation":
                    compilation_score = cat_score.earned_points
                    compilation_ok = compilation_score > 0
                elif cat_score.category_id == "code_quality":
                    code_score = cat_score.earned_points
                elif cat_score.category_id == "report_quality":
                    report_score = cat_score.earned_points

            table_data.append((
                result.student_id,
                result.name,
                compilation_ok,
                code_score,
                report_score,
                result.total_score,
                result.grade
            ))

        # 填充表格
        self.results_table.setRowCount(len(table_data))

        for row, data in enumerate(table_data):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))

                if col == 2:  # 编译列
                    if value:
                        item.setText("✓")
                        item.setForeground(Qt.GlobalColor.green)
                    else:
                        item.setText("✗")
                        item.setForeground(Qt.GlobalColor.red)

                if col == 6:  # 等级列
                    if value == "A":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    elif value == "F":
                        item.setForeground(Qt.GlobalColor.red)

                self.results_table.setItem(row, col, item)

    def show_student_detail(self, index):
        """显示学生详情"""
        row = index.row()
        student_id = self.results_table.item(row, 0).text()
        name = self.results_table.item(row, 1).text()

        self.log(f"查看学生详情: {student_id}-{name}")

        # 查找学生结果
        student_result = None
        if self.current_result and self.current_result.grading_results:
            for result in self.current_result.grading_results:
                if result.student_id == student_id and result.name == name:
                    student_result = result
                    break

        if student_result:
            # 显示详细报告
            detail_text = f"""
            <h3>{student_result.name} 的批阅详情</h3>
            <table border="1" cellpadding="5" cellspacing="0">
            <tr><td><b>学号:</b></td><td>{student_result.student_id}</td></tr>
            <tr><td><b>姓名:</b></td><td>{student_result.name}</td></tr>
            <tr><td><b>班级:</b></td><td>{student_result.class_name}</td></tr>
            <tr><td><b>总分:</b></td><td>{student_result.total_score:.1f}/{student_result.max_score:.1f}</td></tr>
            <tr><td><b>等级:</b></td><td><b>{student_result.grade}</b></td></tr>
            </table>
            <br>
            <h4>各类别得分:</h4>
            <table border="1" cellpadding="5" cellspacing="0">
            <tr><th>类别</th><th>得分</th><th>满分</th></tr>
            """

            for cat_score in student_result.category_scores:
                detail_text += f"""
                <tr>
                <td>{cat_score.category_name}</td>
                <td>{cat_score.earned_points:.1f}</td>
                <td>{cat_score.max_points:.1f}</td>
                </tr>
                """

            detail_text += "</table>"

            if student_result.strengths:
                detail_text += "<br><h4>优点:</h4><ul>"
                for strength in student_result.strengths:
                    detail_text += f"<li>{strength}</li>"
                detail_text += "</ul>"

            if student_result.weaknesses:
                detail_text += "<br><h4>不足:</h4><ul>"
                for weakness in student_result.weaknesses:
                    detail_text += f"<li>{weakness}</li>"
                detail_text += "</ul>"

            QMessageBox.information(self, "学生详情", detail_text)
        else:
            QMessageBox.warning(self, "未找到", f"未找到学生 {student_id}-{name} 的批阅结果")

    def view_class_report(self):
        """查看班级报告"""
        self.log("打开班级报告...")

        # TODO: 打开实际的报告文件
        QMessageBox.information(
            self,
            "班级报告",
            "班级报告功能开发中...\n\n报告将保存在:\noutputs/grading/班级/实验/"
        )

    def export_class_report(self):
        """导出班级报告"""
        self.log("导出班级报告...")

        # TODO: 导出功能
        QMessageBox.information(self, "导出", "导出功能开发中...")

    def export_all_reports(self):
        """导出所有个人报告"""
        self.log("导出所有个人报告...")

        # TODO: 批量导出功能
        QMessageBox.information(self, "导出", "批量导出功能开发中...")

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于",
            """
            <h3>自动化批阅系统 v1.0</h3>
            <p>STM32F407教学项目专用工具</p>
            <p><b>功能：</b></p>
            <ul>
                <li>自动整理提交格式</li>
                <li>批量编译检查</li>
                <li>代码质量分析</li>
                <li>报告自动评分</li>
            </ul>
            <p><b>开发者：</b>STM32F407教学团队</p>
            """
        )
