"""
评分评估视图

提供评分评估的用户界面
"""

from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QCheckBox,
    QComboBox, QSplitter, QTextEdit, QFrame, QGridLayout,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from app.models.domain import ProjectConfig, GradingInfo
from app.core.grading import GradingService
from app.ui.file_dialog_utils import get_open_filename


class GradingView(QWidget):
    """评分评估视图"""

    # 信号
    status_changed = pyqtSignal(str)
    student_selected = pyqtSignal(str)  # 学号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None
        self.grading_service = GradingService(self)
        self.selected_student_id: Optional[str] = None

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

        # 左侧：评分列表
        list_widget = self._create_student_list_section()
        splitter.addWidget(list_widget)

        # 右侧：详情和统计
        detail_widget = self._create_detail_section()
        splitter.addWidget(detail_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 500])

        layout.addWidget(splitter)

    def _create_config_section(self, parent_layout):
        """创建配置区域"""
        group = QGroupBox("评分配置")
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

        # Rubric选择
        rubric_layout = QVBoxLayout()
        rubric_label = QLabel("评分标准 (Rubric):")
        self.rubric_combo = QComboBox()
        self.rubric_combo.setMinimumWidth(300)
        self.rubric_combo.addItem("档位实验评分标准", "car_gear")
        self.rubric_combo.addItem("转向灯实验评分标准", "turn_signal")
        self.rubric_combo.addItem("自定义", "custom")
        # 扫描默认 rubric 目录
        self._scan_rubrics()

        rubric_refresh_btn = QPushButton("🔄")
        rubric_refresh_btn.setToolTip("重新扫描Rubric文件")
        rubric_refresh_btn.setMaximumWidth(40)
        rubric_refresh_btn.clicked.connect(self._scan_rubrics)

        rubric_row = QHBoxLayout()
        rubric_row.addWidget(self.rubric_combo)
        rubric_row.addWidget(rubric_refresh_btn)

        rubric_layout.addWidget(rubric_label)
        rubric_layout.addLayout(rubric_row)

        layout.addLayout(rubric_layout)

        # 评分选项
        options_layout = QVBoxLayout()
        options_label = QLabel("评分选项:")

        self.rubric_grading_cb = QCheckBox("Rubric评分")
        self.rubric_grading_cb.setChecked(True)
        self.technical_check_cb = QCheckBox("技术要点检查")
        self.technical_check_cb.setChecked(True)
        self.code_analysis_cb = QCheckBox("代码深度分析")
        self.code_analysis_cb.setChecked(True)
        self.image_quality_cb = QCheckBox("图像质量检测")
        self.consistency_check_cb = QCheckBox("评分一致性校验")

        options_row = QGridLayout()
        options_row.addWidget(self.rubric_grading_cb, 0, 0)
        options_row.addWidget(self.technical_check_cb, 0, 1)
        options_row.addWidget(self.code_analysis_cb, 1, 0)
        options_row.addWidget(self.image_quality_cb, 1, 1)
        options_row.addWidget(self.consistency_check_cb, 2, 0)

        options_layout.addWidget(options_label)
        options_layout.addLayout(options_row)

        layout.addLayout(options_layout)

        # 控制按钮
        control_layout = QVBoxLayout()
        control_label = QLabel("控制:")

        self.start_btn = QPushButton("🚀 开始评分")
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
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        parent_layout.addWidget(group)

    def _create_student_list_section(self) -> QWidget:
        """创建学生列表区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title = QLabel("学生评分列表")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")

        # 搜索框
        search_layout = QHBoxLayout()
        self.search_label = QLabel("🔍")
        self.search_input = QTextEdit()
        self.search_input.setMaximumHeight(25)
        self.search_input.setPlaceholderText("搜索学号或姓名...")
        search_layout.addWidget(self.search_label)
        search_layout.addWidget(self.search_input)

        # 学生列表表格
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(5)
        self.student_table.setHorizontalHeaderLabels([
            "学号", "姓名", "总分", "等级", "状态"
        ])

        self.student_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.student_table.horizontalHeader().setStretchLastSection(True)
        self.student_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.student_table.setSortingEnabled(True)

        self.student_table.setStyleSheet("""
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

        self.student_table.itemClicked.connect(self._on_student_selected)

        layout.addWidget(title)
        layout.addLayout(search_layout)
        layout.addWidget(self.student_table)

        return widget

    def _create_detail_section(self) -> QWidget:
        """创建详情区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)

        content = QWidget()
        content_layout = QVBoxLayout(content)

        # 进度区域
        progress_group = QGroupBox("评分进度")
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

        self.grading_status_label = QLabel("就绪")
        self.grading_status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;
                padding: 5px;
            }
        """)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.grading_status_label)
        progress_group.setLayout(progress_layout)

        content_layout.addWidget(progress_group)

        # 评分分布图表
        distribution_group = QGroupBox("等级分布")
        distribution_layout = QVBoxLayout()

        self.distribution_label = QLabel("等待评分结果...")
        self.distribution_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.distribution_label.setStyleSheet("""
            QLabel {
                padding: 30px;
                background-color: #f8f9fa;
                border-radius: 8px;
                color: #6c757d;
            }
        """)

        distribution_layout.addWidget(self.distribution_label)
        distribution_group.setLayout(distribution_layout)

        content_layout.addWidget(distribution_group)

        # 统计信息
        stats_group = QGroupBox("评分统计")
        stats_layout = QGridLayout()

        self.avg_label = QLabel("平均分: --")
        self.max_label = QLabel("最高分: --")
        self.min_label = QLabel("最低分: --")
        self.count_label = QLabel("已评分: 0")

        for i, label in enumerate([self.avg_label, self.max_label, self.min_label, self.count_label]):
            label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    font-weight: bold;
                    color: #495057;
                }
            """)
            stats_layout.addWidget(label, 0, i)

        stats_group.setLayout(stats_layout)
        content_layout.addWidget(stats_group)

        # 学生详情
        detail_group = QGroupBox("学生评分详情")
        detail_layout = QVBoxLayout()

        self.detail_label = QLabel("选择一个学生查看详情")
        self.detail_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.detail_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }
        """)

        detail_scroll = QScrollArea()
        detail_scroll.setWidget(self.detail_label)
        detail_scroll.setWidgetResizable(True)

        detail_layout.addWidget(detail_scroll)
        detail_group.setLayout(detail_layout)

        content_layout.addWidget(detail_group, 1)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _connect_signals(self):
        """连接信号"""
        self.start_btn.clicked.connect(self._on_start_grading)
        self.stop_btn.clicked.connect(self._on_stop_grading)

        self.grading_service.progress_updated.connect(self._on_progress_updated)
        self.grading_service.grading_finished.connect(self._on_grading_finished)
        self.grading_service.grading_failed.connect(self._on_grading_failed)

    def _on_select_rubric(self):
        """选择Rubric文件（手动添加到下拉框）"""
        from app.ui.file_dialog_utils import DialogStartDir
        data_dir = DialogStartDir._get_data_dir()
        if data_dir:
            if (data_dir / 'rubrics').exists():
                DialogStartDir._last_dirs['rubric'] = str(data_dir / 'rubrics')

        file_path, _ = get_open_filename(
            self,
            "选择Rubric文件",
            "JSON文件 (*.json)",
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

    def _scan_rubrics(self):
        """扫描可用的Rubric文件"""
        from app.ui.file_dialog_utils import DialogStartDir

        # 保存当前选择
        current_data = self.rubric_combo.currentData()

        self.rubric_combo.clear()
        self.rubric_combo.addItem("档位实验评分标准", "car_gear")
        self.rubric_combo.addItem("转向灯实验评分标准", "turn_signal")
        self.rubric_combo.addItem("自定义", "custom")

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

    def _on_start_grading(self):
        """开始评分"""
        if not self.current_config or not self.current_config.submissions_dir:
            self.grading_status_label.setText("请先在概览界面选择作业目录并确认配置")
            self.grading_status_label.setStyleSheet("color: #dc3545; padding: 5px;")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.student_table.setRowCount(0)

        # 更新配置
        if self.current_config:
            # 从下拉框获取 Rubric 路径
            rubric_data = self.rubric_combo.currentData()
            if rubric_data and rubric_data not in ["car_gear", "turn_signal", "custom"]:
                # 实际的文件路径
                self.current_config.rubric_path = Path(rubric_data)
            elif rubric_data == "custom":
                # 如果选择自定义但没有指定文件，提示用户
                self.status_changed.emit("请选择自定义 Rubric 文件")
                self._reset_ui()
                return

        self.grading_service.start_grading(self.current_config)

    def _on_stop_grading(self):
        """停止评分"""
        self.grading_service.stop_grading()
        self._reset_ui()

    def _on_student_selected(self, item):
        """学生选中"""
        row = item.row()
        student_id = self.student_table.item(row, 0).text()
        self.selected_student_id = student_id
        self.student_selected.emit(student_id)
        self._display_student_detail(student_id)

    def _on_progress_updated(self, progress: int, message: str):
        """进度更新"""
        self.progress_bar.setValue(progress)
        self.grading_status_label.setText(message)

    def _on_grading_finished(self, results: dict):
        """评分完成"""
        self._reset_ui()
        self._display_results(results)
        self.status_changed.emit("评分评估完成")

    def _on_grading_failed(self, error: str):
        """评分失败"""
        self._reset_ui()
        self.grading_status_label.setText(f"评分失败: {error}")

    def _display_results(self, results: dict):
        """显示评分结果"""
        students = results.get('students', [])

        # 填充学生列表
        self.student_table.setRowCount(0)

        for i, student in enumerate(students):
            self.student_table.insertRow(i)

            self.student_table.setItem(i, 0, QTableWidgetItem(student.get('student_id', '')))
            self.student_table.setItem(i, 1, QTableWidgetItem(student.get('name', '')))

            score = student.get('total_score', 0)
            score_item = QTableWidgetItem(f"{score:.1f}")
            self.student_table.setItem(i, 2, score_item)

            grade = student.get('grade', 'F')
            grade_item = QTableWidgetItem(grade)
            grade_item.setForeground(self._get_grade_color(grade))
            self.student_table.setItem(i, 3, grade_item)

            status_item = QTableWidgetItem("✅ 已评分")
            status_item.setForeground(QColor(0x28a745))
            self.student_table.setItem(i, 4, status_item)

        # 更新统计
        stats = self.grading_service.get_score_statistics()
        if stats:
            self.avg_label.setText(f"平均分: {stats['average']:.1f}")
            self.max_label.setText(f"最高分: {stats['highest']:.1f}")
            self.min_label.setText(f"最低分: {stats['lowest']:.1f}")
            self.count_label.setText(f"已评分: {stats['count']}")

        # 更新分布
        distribution = self.grading_service.get_grade_distribution()
        self._display_distribution(distribution)

    def _display_distribution(self, distribution: dict):
        """显示等级分布"""
        total = sum(distribution.values())
        if total == 0:
            return

        # 创建简单的ASCII图表
        chart_lines = []
        chart_lines.append("<div style='font-family: monospace;'>")
        chart_lines.append("<h3>等级分布</h3>")

        colors = {
            'A': '#28a745',
            'B': '#5cb85c',
            'C': '#ffc107',
            'D': '#fd7e14',
            'F': '#dc3545'
        }

        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = distribution.get(grade, 0)
            bar_length = int(count / total * 50) if total > 0 else 0
            bar = '█' * bar_length

            chart_lines.append(f"<div style='color: {colors[grade]}; margin: 5px 0;'>")
            chart_lines.append(f"{grade}: {bar} {count}人 ({count/total*100:.1f}%)")
            chart_lines.append("</div>")

        chart_lines.append("</div>")

        self.distribution_label.setText(''.join(chart_lines))

    def _display_student_detail(self, student_id: str):
        """显示学生详情"""
        grading = self.grading_service.get_student_grading(student_id)

        if not grading:
            self.detail_label.setText("未找到该学生的评分信息")
            return

        # 构建详情HTML
        html = f"""
        <h2 style='color: #2c3e50;'>{grading.name} ({grading.student_id})</h2>
        <h3 style='color: #3498db;'>总分: {grading.total_score:.1f}/{grading.max_score} ({grading.percentage:.1f}%)</h3>
        <h3 style='color: {self._get_grade_hex(grading.grade)};'>等级: {grading.grade}</h3>

        <h4 style='margin-top: 20px;'>优势</h4>
        <ul>
        """

        for strength in grading.strengths:
            html += f"<li>✅ {strength}</li>"

        html += """
        </ul>

        <h4 style='margin-top: 15px;'>不足</h4>
        <ul>
        """

        for weakness in grading.weaknesses:
            html += f"<li>⚠️ {weakness}</li>"

        if grading.technical_issues:
            html += """
            </ul>

            <h4 style='margin-top: 15px;'>技术问题</h4>
            <ul>
            """
            for issue in grading.technical_issues:
                html += f"<li>🔧 {issue}</li>"

        if grading.improvement_suggestions:
            html += """
            </ul>

            <h4 style='margin-top: 15px;'>改进建议</h4>
            <ul>
            """
            for suggestion in grading.improvement_suggestions:
                html += f"<li>💡 {suggestion}</li>"

        html += "</ul>"

        self.detail_label.setText(html)

    def _get_grade_color(self, grade: str) -> QBrush:
        """获取等级颜色"""
        colors = {
            'A': QColor(0x28a745),
            'B': QColor(0x5cb85c),
            'C': QColor(0xffc107),
            'D': QColor(0xfd7e14),
            'F': QColor(0xdc3545)
        }
        return QBrush(colors.get(grade, QColor(0x6c757d)))

    def _get_grade_hex(self, grade: str) -> str:
        """获取等级十六进制颜色"""
        colors = {
            'A': '#28a745',
            'B': '#5cb85c',
            'C': '#ffc107',
            'D': '#fd7e14',
            'F': '#dc3545'
        }
        return colors.get(grade, '#6c757d')

    def _reset_ui(self):
        """重置UI状态"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def set_config(self, config: ProjectConfig):
        """设置项目配置"""
        self.current_config = config
