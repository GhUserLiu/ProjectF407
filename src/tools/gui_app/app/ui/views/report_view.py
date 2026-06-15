"""
报告输出视图

提供报告生成的用户界面
"""

from pathlib import Path
from typing import Optional, List
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QGroupBox, QCheckBox,
    QComboBox, QSpinBox, QTextEdit, QFrame, QGridLayout,
    QProgressBar, QDateTimeEdit, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QDateTime
from PyQt6.QtGui import QColor

from app.models.domain import ProjectConfig
from app.utils.workers import ReportWorker
from app.ui.file_dialog_utils import get_existing_directory


class ReportView(QWidget):
    """报告输出视图"""

    # 信号
    status_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_config: Optional[ProjectConfig] = None
        self.plagiarism_results: Optional[dict] = None
        self.grading_results: Optional[dict] = None
        self._worker: Optional[ReportWorker] = None

        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
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
            QTabBar::tab:hover {
                background-color: #e9ecef;
            }
        """)

        # 成绩报告标签页
        grade_tab = self._create_grade_report_tab()
        self.tab_widget.addTab(grade_tab, "📊 成绩报告")

        # 查重报告标签页
        plagiarism_tab = self._create_plagiarism_report_tab()
        self.tab_widget.addTab(plagiarism_tab, "🔍 查重报告")

        # 统计分析标签页
        stats_tab = self._create_statistics_tab()
        self.tab_widget.addTab(stats_tab, "📈 统计分析")

        layout.addWidget(self.tab_widget)

    def _create_grade_report_tab(self) -> QWidget:
        """创建成绩报告标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 配置区域
        config_group = QGroupBox("报告配置")
        config_group.setStyleSheet("""
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

        config_layout = QGridLayout()

        # 报告类型
        config_layout.addWidget(QLabel("报告类型:"), 0, 0)
        self.grade_report_type = QComboBox()
        self.grade_report_type.addItem("简明成绩表", "simple")
        self.grade_report_type.addItem("详细成绩表", "detailed")
        self.grade_report_type.addItem("按等级分组", "by_grade")
        config_layout.addWidget(self.grade_report_type, 0, 1)

        # 包含选项
        options_group = QGroupBox("包含内容")
        options_layout = QGridLayout()

        self.include_details_cb = QCheckBox("包含详细评分")
        self.include_details_cb.setChecked(True)
        self.include_feedback_cb = QCheckBox("包含反馈摘要")
        self.include_feedback_cb.setChecked(True)
        self.include_similarity_cb = QCheckBox("包含相似度信息")
        self.include_similarity_cb.setChecked(False)
        self.include_rank_cb = QCheckBox("包含排名")
        self.include_rank_cb.setChecked(True)

        options_layout.addWidget(self.include_details_cb, 0, 0)
        options_layout.addWidget(self.include_feedback_cb, 0, 1)
        options_layout.addWidget(self.include_similarity_cb, 1, 0)
        options_layout.addWidget(self.include_rank_cb, 1, 1)

        options_group.setLayout(options_layout)
        config_layout.addWidget(options_group, 1, 0, 1, 2)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 操作按钮
        action_layout = QHBoxLayout()

        self.generate_grade_btn = QPushButton("🚀 生成成绩报告")
        self.generate_grade_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
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
        self.generate_grade_btn.clicked.connect(self._on_generate_grade_report)

        self.open_grade_btn = QPushButton("📂 打开输出目录")
        self.open_grade_btn.clicked.connect(self._on_open_output_dir)

        action_layout.addStretch()
        action_layout.addWidget(self.generate_grade_btn)
        action_layout.addWidget(self.open_grade_btn)

        layout.addLayout(action_layout)

        # 预览区域
        preview_group = QGroupBox("报告预览")
        preview_layout = QVBoxLayout()

        self.grade_preview = QTextEdit()
        self.grade_preview.setReadOnly(True)
        self.grade_preview.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        self.grade_preview.setText("等待生成报告...")

        preview_layout.addWidget(self.grade_preview)
        preview_group.setLayout(preview_layout)

        layout.addWidget(preview_group, 1)

        return widget

    def _create_plagiarism_report_tab(self) -> QWidget:
        """创建查重报告标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 配置区域
        config_group = QGroupBox("查重报告配置")
        config_layout = QGridLayout()

        # 报告格式
        config_layout.addWidget(QLabel("报告格式:"), 0, 0)
        self.plagiarism_format = QComboBox()
        self.plagiarism_format.addItem("Excel工作簿", "excel")
        self.plagiarism_format.addItem("HTML报告", "html")
        self.plagiarism_format.addItem("PDF报告", "pdf")
        config_layout.addWidget(self.plagiarism_format, 0, 1)

        # 过滤选项
        filter_group = QGroupBox("过滤选项")
        filter_layout = QGridLayout()

        self.only_suspicious_cb = QCheckBox("仅显示可疑对")
        self.only_suspicious_cb.setChecked(False)
        self.min_similarity_spin = QSpinBox()
        self.min_similarity_spin.setRange(0, 100)
        self.min_similarity_spin.setValue(50)
        self.min_similarity_spin.setSuffix("%")
        self.min_similarity_spin.setToolTip("最小相似度阈值")

        filter_layout.addWidget(self.only_suspicious_cb, 0, 0)
        filter_layout.addWidget(QLabel("最小相似度:"), 0, 1)
        filter_layout.addWidget(self.min_similarity_spin, 0, 2)

        filter_group.setLayout(filter_layout)
        config_layout.addWidget(filter_group, 1, 0, 1, 3)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 操作按钮
        action_layout = QHBoxLayout()

        self.generate_plagiarism_btn = QPushButton("🚀 生成查重报告")
        self.generate_plagiarism_btn.setStyleSheet("""
            QPushButton {
                padding: 12px 24px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.generate_plagiarism_btn.clicked.connect(self._on_generate_plagiarism_report)

        action_layout.addStretch()
        action_layout.addWidget(self.generate_plagiarism_btn)

        layout.addLayout(action_layout)

        # 查重结果预览
        preview_group = QGroupBox("查重结果预览")
        preview_layout = QVBoxLayout()

        self.plagiarism_preview = QTextEdit()
        self.plagiarism_preview.setReadOnly(True)
        self.plagiarism_preview.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                font-family: Consolas, monospace;
                font-size: 12px;
            }
        """)
        self.plagiarism_preview.setText("等待生成报告...")

        preview_layout.addWidget(self.plagiarism_preview)
        preview_group.setLayout(preview_layout)

        layout.addWidget(preview_group, 1)

        return widget

    def _create_statistics_tab(self) -> QWidget:
        """创建统计分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 统计概览
        overview_group = QGroupBox("统计概览")
        overview_layout = QGridLayout()

        # 成绩统计
        grade_stats_group = QGroupBox("成绩统计")
        grade_stats_layout = QGridLayout()

        self.avg_score_label = QLabel("平均分: --")
        self.max_score_label = QLabel("最高分: --")
        self.min_score_label = QLabel("最低分: --")
        self.pass_rate_label = QLabel("及格率: --")

        for i, label in enumerate([self.avg_score_label, self.max_score_label,
                                    self.min_score_label, self.pass_rate_label]):
            label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    font-weight: bold;
                    color: #495057;
                }
            """)
            grade_stats_layout.addWidget(label, i // 2, i % 2)

        grade_stats_group.setLayout(grade_stats_layout)
        overview_layout.addWidget(grade_stats_group, 0, 0)

        # 等级分布
        grade_dist_group = QGroupBox("等级分布")
        grade_dist_layout = QVBoxLayout()

        self.grade_dist_label = QLabel("等待数据...")
        self.grade_dist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grade_dist_label.setStyleSheet("""
            QLabel {
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
            }
        """)

        grade_dist_layout.addWidget(self.grade_dist_label)
        grade_dist_group.setLayout(grade_dist_layout)
        overview_layout.addWidget(grade_dist_group, 0, 1)

        # 查重统计
        plagiarism_stats_group = QGroupBox("查重统计")
        plagiarism_stats_layout = QGridLayout()

        self.total_pairs_label = QLabel("对比对数: --")
        self.suspicious_pairs_label = QLabel("可疑对数: --")
        self.plagiarism_pairs_label = QLabel("抄袭对数: --")
        self.cross_group_label = QLabel("跨组对比: --")

        for i, label in enumerate([self.total_pairs_label, self.suspicious_pairs_label,
                                    self.plagiarism_pairs_label, self.cross_group_label]):
            label.setStyleSheet("""
                QLabel {
                    padding: 10px;
                    background-color: #f8f9fa;
                    border-radius: 4px;
                    font-weight: bold;
                    color: #495057;
                }
            """)
            plagiarism_stats_layout.addWidget(label, i // 2, i % 2)

        plagiarism_stats_group.setLayout(plagiarism_stats_layout)
        overview_layout.addWidget(plagiarism_stats_group, 1, 0)

        # 导出选项
        export_group = QGroupBox("导出选项")
        export_layout = QHBoxLayout()

        self.export_stats_btn = QPushButton("📤 导出统计数据")
        self.export_stats_btn.clicked.connect(self._on_export_statistics)

        export_layout.addWidget(self.export_stats_btn)
        export_layout.addStretch()

        export_group.setLayout(export_layout)
        overview_layout.addWidget(export_group, 1, 1)

        overview_group.setLayout(overview_layout)
        layout.addWidget(overview_group)

        return widget

    def _on_generate_grade_report(self):
        """生成成绩报告"""
        if not self.grading_results:
            self.grade_preview.setText("❌ 没有可用的评分数据")
            return

        # 选择输出目录
        directory = get_existing_directory(
            self,
            "选择输出目录",
            'output',
            self.current_config
        )
        if not directory:
            return

        output_path = Path(directory) / "成绩报告.xlsx"

        # 创建报告生成工作线程
        report_type = self.grade_report_type.currentData()

        self._worker = ReportWorker(
            report_type=report_type,
            data=self.grading_results,
            output_path=str(output_path)
        )

        self._worker.finished.connect(self._on_grade_report_finished)
        self._worker.error_occurred.connect(self._on_report_error)
        self._worker.start()

        self.grade_preview.setText(f"正在生成成绩报告...\n输出路径: {output_path}")

    def _on_generate_plagiarism_report(self):
        """生成查重报告"""
        if not self.plagiarism_results:
            self.plagiarism_preview.setText("❌ 没有可用的查重数据")
            return

        # 选择输出目录
        directory = get_existing_directory(
            self,
            "选择输出目录",
            'output',
            self.current_config
        )
        if not directory:
            return

        format_type = self.plagiarism_format.currentData()
        extensions = {'excel': '.xlsx', 'html': '.html', 'pdf': '.pdf'}
        ext = extensions.get(format_type, '.xlsx')

        output_path = Path(directory) / f"查重报告{ext}"

        self._worker = ReportWorker(
            report_type=format_type,
            data=self.plagiarism_results,
            output_path=str(output_path)
        )

        self._worker.finished.connect(self._on_plagiarism_report_finished)
        self._worker.error_occurred.connect(self._on_report_error)
        self._worker.start()

        self.plagiarism_preview.setText(f"正在生成查重报告...\n输出路径: {output_path}")

    def _on_grade_report_finished(self, output_path: str):
        """成绩报告生成完成"""
        self.grade_preview.setText(f"✅ 成绩报告生成成功！\n\n输出路径: {output_path}")
        self.status_changed.emit(f"成绩报告已生成: {output_path}")

    def _on_plagiarism_report_finished(self, output_path: str):
        """查重报告生成完成"""
        self.plagiarism_preview.setText(f"✅ 查重报告生成成功！\n\n输出路径: {output_path}")
        self.status_changed.emit(f"查重报告已生成: {output_path}")

    def _on_report_error(self, error: str):
        """报告生成错误"""
        self.grade_preview.setText(f"❌ 报告生成失败: {error}")
        self.status_changed.emit(f"报告生成失败: {error}")

    def _on_open_output_dir(self):
        """打开输出目录"""
        if self.current_config and self.current_config.output_dir:
            import os
            import subprocess
            path = str(self.current_config.output_dir)
            if os.path.exists(path):
                if os.name == 'nt':  # Windows
                    os.startfile(path)
                else:  # Mac/Linux
                    subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', path])

    def _on_export_statistics(self):
        """导出统计数据"""
        directory = get_existing_directory(
            self,
            "选择输出目录",
            'output',
            self.current_config
        )
        if not directory:
            return

        output_path = Path(directory) / "统计数据.json"

        stats = {
            'grade_stats': self._get_grade_stats(),
            'plagiarism_stats': self._get_plagiarism_stats()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        self.status_changed.emit(f"统计数据已导出: {output_path}")

    def _get_grade_stats(self) -> dict:
        """获取成绩统计"""
        if not self.grading_results:
            return {}

        students = self.grading_results.get('students', [])
        scores = [s.get('total_score', 0) for s in students]

        if not scores:
            return {}

        return {
            'average': sum(scores) / len(scores),
            'max': max(scores),
            'min': min(scores),
            'count': len(scores),
            'pass_rate': len([s for s in scores if s >= 60]) / len(scores) * 100
        }

    def _get_plagiarism_stats(self) -> dict:
        """获取查重统计"""
        if not self.plagiarism_results:
            return {}

        return {
            'total_pairs': self.plagiarism_results.get('total_pairs', 0),
            'suspicious_count': self.plagiarism_results.get('suspicious_count', 0),
            'plagiarism_count': self.plagiarism_results.get('plagiarism_count', 0),
            'cross_group_count': len([
                p for p in self.plagiarism_results.get('similarity_pairs', [])
                if p.get('is_cross_group', False)
            ])
        }

    def set_config(self, config: ProjectConfig):
        """设置项目配置"""
        self.current_config = config

    def set_plagiarism_results(self, results: dict):
        """设置查重结果"""
        self.plagiarism_results = results
        self._update_plagiarism_stats()

    def set_grading_results(self, results: dict):
        """设置评分结果"""
        self.grading_results = results
        self._update_grade_stats()

    def _update_grade_stats(self):
        """更新成绩统计显示"""
        if not self.grading_results:
            return

        students = self.grading_results.get('students', [])
        scores = [s.get('total_score', 0) for s in students]

        if scores:
            self.avg_score_label.setText(f"平均分: {sum(scores)/len(scores):.1f}")
            self.max_score_label.setText(f"最高分: {max(scores):.1f}")
            self.min_score_label.setText(f"最低分: {min(scores):.1f}")

            pass_count = len([s for s in scores if s >= 60])
            self.pass_rate_label.setText(f"及格率: {pass_count/len(scores)*100:.1f}%")

        # 更新等级分布
        distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for student in students:
            grade = student.get('grade', 'F')
            distribution[grade] = distribution.get(grade, 0) + 1

        total = len(students)
        chart = []
        colors = {'A': '#28a745', 'B': '#5cb85c', 'C': '#ffc107', 'D': '#fd7e14', 'F': '#dc3545'}

        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = distribution.get(grade, 0)
            bar_length = int(count / total * 30) if total > 0 else 0
            bar = '█' * bar_length
            chart.append(f"<div style='color: {colors[grade]}; margin: 3px 0;'>{grade}: {bar} {count}人</div>")

        self.grade_dist_label.setText(f"<div style='font-family: monospace;'>{''.join(chart)}</div>")

    def _update_plagiarism_stats(self):
        """更新查重统计显示"""
        if not self.plagiarism_results:
            return

        self.total_pairs_label.setText(f"对比对数: {self.plagiarism_results.get('total_pairs', 0)}")
        self.suspicious_pairs_label.setText(f"可疑对数: {self.plagiarism_results.get('suspicious_count', 0)}")
        self.plagiarism_pairs_label.setText(f"抄袭对数: {self.plagiarism_results.get('plagiarism_count', 0)}")

        cross_group = len([
            p for p in self.plagiarism_results.get('similarity_pairs', [])
            if p.get('is_cross_group', False)
        ])
        self.cross_group_label.setText(f"跨组对比: {cross_group}")

import sys
