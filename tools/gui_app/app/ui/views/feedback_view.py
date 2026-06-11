"""
反馈生成视图

提供反馈生成的用户界面
"""

from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QComboBox,
    QSplitter, QTextEdit, QFrame, QListWidget, QListWidgetItem,
    QProgressBar, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from app.models.domain import ProjectConfig, FeedbackStyle
from app.utils.workers import FeedbackWorker


class FeedbackView(QWidget):
    """反馈生成视图"""

    # 信号
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None
        self.grading_results: Optional[dict] = None
        self.feedback_results: dict = {}
        self._worker: Optional[FeedbackWorker] = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 顶部配置区域
        self._create_config_section(layout)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：学生列表
        list_widget = self._create_student_list_section()
        splitter.addWidget(list_widget)

        # 右侧：预览和编辑
        preview_widget = self._create_preview_section()
        splitter.addWidget(preview_widget)

        # 设置分割比例
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

    def _create_config_section(self, parent_layout):
        """创建配置区域"""
        group = QGroupBox("反馈配置")
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

        # 反馈风格
        style_layout = QVBoxLayout()
        style_label = QLabel("反馈风格:")

        self.style_combo = QComboBox()
        self.style_combo.addItem("详细", "detailed")
        self.style_combo.addItem("标准", "standard")
        self.style_combo.addItem("简洁", "concise")
        self.style_combo.addItem("鼓励", "encouraging")
        self.style_combo.addItem("技术", "technical")

        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo)
        style_layout.addStretch()

        layout.addLayout(style_layout)

        # 输出格式
        format_layout = QVBoxLayout()
        format_label = QLabel("输出格式:")

        self.format_combo = QComboBox()
        self.format_combo.addItem("Markdown (.md)", "md")
        self.format_combo.addItem("HTML (.html)", "html")
        self.format_combo.addItem("纯文本 (.txt)", "txt")

        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addStretch()

        layout.addLayout(format_layout)

        # 包含相似度
        similarity_layout = QVBoxLayout()
        similarity_label = QLabel("选项:")

        self.include_similarity_cb = QCheckBox("包含相似度信息")
        self.include_similarity_cb.setChecked(True)
        self.include_improvement_cb = QCheckBox("包含改进建议")
        self.include_improvement_cb.setChecked(True)

        similarity_layout.addWidget(similarity_label)
        similarity_layout.addWidget(self.include_similarity_cb)
        similarity_layout.addWidget(self.include_improvement_cb)
        similarity_layout.addStretch()

        layout.addLayout(similarity_layout)

        # 控制按钮
        control_layout = QVBoxLayout()

        self.generate_all_btn = QPushButton("🚀 批量生成")
        self.generate_all_btn.setStyleSheet("""
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

        self.export_btn = QPushButton("📤 导出全部")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_all)

        control_layout.addWidget(self.generate_all_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addWidget(self.export_btn)
        control_layout.addStretch()

        layout.addLayout(control_layout)

        # 进度
        progress_layout = QVBoxLayout()
        progress_label = QLabel("进度:")

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

        progress_layout.addWidget(progress_label)
        progress_layout.addWidget(self.progress_bar)

        layout.addLayout(progress_layout)

        parent_layout.addWidget(group)

    def _create_student_list_section(self) -> QWidget:
        """创建学生列表区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题
        title = QLabel("学生列表")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")

        # 学生列表
        self.student_list = QListWidget()
        self.student_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background-color: #f8f9fa;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
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
        self.student_list.itemClicked.connect(self._on_student_selected)

        # 操作按钮
        action_layout = QHBoxLayout()

        self.generate_one_btn = QPushButton("生成单个")
        self.generate_one_btn.clicked.connect(self._on_generate_one)

        self.export_one_btn = QPushButton("导出")
        self.export_one_btn.clicked.connect(self._on_export_one)

        action_layout.addWidget(self.generate_one_btn)
        action_layout.addWidget(self.export_one_btn)

        layout.addWidget(title)
        layout.addWidget(self.student_list)
        layout.addLayout(action_layout)

        return widget

    def _create_preview_section(self) -> QWidget:
        """创建预览区域"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 标题区域
        title_layout = QHBoxLayout()

        self.preview_title = QLabel("反馈预览")
        self.preview_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.student_info_label = QLabel()
        self.student_info_label.setStyleSheet("color: #6c757d;")

        title_layout.addWidget(self.preview_title)
        title_layout.addStretch()
        title_layout.addWidget(self.student_info_label)

        layout.addLayout(title_layout)

        # 创建分割器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 渲染预览
        render_widget = self._create_render_preview()
        splitter.addWidget(render_widget)

        # 源代码编辑
        edit_widget = self._create_source_editor()
        splitter.addWidget(edit_widget)

        splitter.setSizes([300, 200])

        layout.addWidget(splitter)

        return widget

    def _create_render_preview(self) -> QWidget:
        """创建渲染预览"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        preview_label = QLabel("渲染预览")
        preview_label.setStyleSheet("font-weight: bold; color: #495057;")

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                font-size: 13px;
                line-height: 1.6;
            }
        """)

        layout.addWidget(preview_label)
        layout.addWidget(self.preview_text)

        return widget

    def _create_source_editor(self) -> QWidget:
        """创建源代码编辑器"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        editor_label = QLabel("源代码 (可编辑)")
        editor_label.setStyleSheet("font-weight: bold; color: #495057;")

        self.source_text = QTextEdit()
        self.source_text.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 8px;
                padding: 15px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        self.source_text.textChanged.connect(self._on_source_changed)

        layout.addWidget(editor_label)
        layout.addWidget(self.source_text)

        return widget

    def _on_student_selected(self, item):
        """学生选中"""
        student_id = item.data(Qt.ItemDataRole.UserRole)
        self._display_feedback(student_id)

    def _on_source_changed(self):
        """源代码变化"""
        content = self.source_text.toPlainText()
        self.preview_text.setText(self._render_markdown(content))

    def _on_generate_one(self):
        """生成单个反馈"""
        current_item = self.student_list.currentItem()
        if current_item:
            student_id = current_item.data(Qt.ItemDataRole.UserRole)
            self._generate_feedback_for_student(student_id)

    def _on_generate_all(self):
        """批量生成"""
        if self._worker and self._worker.isRunning():
            return

        self.generate_all_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self._worker = FeedbackWorker(
            config=self.current_config.to_dict() if self.current_config else {},
            grading_results=self.grading_results or {},
            style=self.style_combo.currentData()
        )

        self._worker.item_completed.connect(self._on_item_completed)
        self._worker.finished.connect(self._on_batch_finished)
        self._worker.progress_updated.connect(self.progress_bar.setValue)
        self._worker.start()

    def _on_stop(self):
        """停止生成"""
        if self._worker:
            self._worker.stop()
            self._reset_ui()

    def _on_export_one(self):
        """导出单个"""
        current_item = self.student_list.currentItem()
        if current_item:
            student_id = current_item.data(Qt.ItemDataRole.UserRole)
            self._export_feedback(student_id)

    def _on_export_all(self):
        """导出全部"""
        directory = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if directory:
            # TODO: 批量导出
            self.status_changed.emit(f"反馈已导出到: {directory}")

    def _on_item_completed(self, student_id: str, content: str):
        """单个完成"""
        self.feedback_results[student_id] = content

        # 更新列表项状态
        for i in range(self.student_list.count()):
            item = self.student_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == student_id:
                item.setText(f"✅ {item.text()[2:]}")  # 添加完成标记
                break

        # 如果当前选中的是这个学生，显示反馈
        current_item = self.student_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) == student_id:
            self._display_feedback(student_id)

    def _on_batch_finished(self, results: dict):
        """批量完成"""
        self.feedback_results = results
        self.export_btn.setEnabled(True)
        self._reset_ui()
        self.status_changed.emit(f"批量生成完成 - 共 {len(results)} 份反馈")

    def _generate_feedback_for_student(self, student_id: str):
        """为单个学生生成反馈"""
        # TODO: 实现单个生成逻辑
        self.status_changed.emit(f"正在为 {student_id} 生成反馈...")

    def _display_feedback(self, student_id: str):
        """显示反馈"""
        if student_id in self.feedback_results:
            content = self.feedback_results[student_id]
            self.source_text.setText(content)
            self.preview_text.setText(self._render_markdown(content))

            # 更新学生信息
            for i in range(self.student_list.count()):
                item = self.student_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == student_id:
                    self.student_info_label.setText(item.text())
                    break

    def _export_feedback(self, student_id: str):
        """导出反馈"""
        if student_id not in self.feedback_results:
            return

        content = self.feedback_results[student_id]
        format_type = self.format_combo.currentData()

        # 确定文件扩展名
        extensions = {'md': '.md', 'html': '.html', 'txt': '.txt'}
        ext = extensions.get(format_type, '.md')

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存反馈",
            f"feedback_{student_id}{ext}",
            f"{format_type.upper()}文件 (*{ext})"
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.status_changed.emit(f"反馈已保存: {file_path}")

    def _render_markdown(self, text: str) -> str:
        """简单渲染Markdown"""
        # 简单的Markdown到HTML转换
        html = text

        # 标题
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', 1)
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', 1)
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)

        # 粗体
        html = html.replace('**', '<strong>', 1).replace('**', '</strong>', 1)

        # 列表
        lines = html.split('\n')
        in_list = False
        result_lines = []

        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                result_lines.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)

        if in_list:
            result_lines.append('</ul>')

        html = '\n'.join(result_lines)

        return f"""
        <div style='font-family: "Microsoft YaHei", sans-serif; line-height: 1.6;'>
            {html}
        </div>
        """

    def _reset_ui(self):
        """重置UI状态"""
        self.generate_all_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def set_config(self, config: ProjectConfig):
        """设置项目配置"""
        self.current_config = config

    def set_grading_results(self, results: dict):
        """设置评分结果"""
        self.grading_results = results

        # 清空并填充学生列表
        self.student_list.clear()

        for student in results.get('students', []):
            item = QListWidgetItem(f"📝 {student.get('name', '')} ({student.get('student_id', '')})")
            item.setData(Qt.ItemDataRole.UserRole, student.get('student_id'))
            self.student_list.addItem(item)
