#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
反馈生成面板（批量 + 双模式）
Feedback Generation Panel

两种输出：
- 学生反馈：每个学生的丰富文本，解释评分依据、失分点与可提升方向；
- 教师分析报告：班级成绩统计、等级分布、各维度薄弱分析、排名、共性问题。

输入取自「数据源」页（多班级），批量生成。
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton,
    QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QProgressBar,
)
from PyQt6.QtGui import QFont

from tools.teaching_management_gui.data_source import shared
from tools.teaching_management_gui.feedback_reports import (
    build_student_feedback,
    build_teacher_report,
)
from tools.teaching_management_gui.workers.feedback_worker import FeedbackWorker


class FeedbackPanel(QWidget):
    """反馈生成面板（教师分析报告 / 学生反馈）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_generating = False
        self.reports = []   # [(report_dict, class_name), ...]
        self.feedback_worker = None

        self.setup_ui()
        shared().entries_changed.connect(self._refresh_data_source_status)
        self._refresh_data_source_status()
        self._on_mode_changed()  # 初始化子选项可见性
        # 学生模式下，切换详细度/包含项时自动刷新预览
        self.feedback_type.currentIndexChanged.connect(self._auto_preview)
        self.include_strengths.toggled.connect(self._auto_preview)
        self.include_weaknesses.toggled.connect(self._auto_preview)
        self.include_suggestions.toggled.connect(self._auto_preview)

    # ---------------- UI ----------------
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self._create_config_panel())
        layout.addWidget(self._create_preview_panel(), 1)
        layout.addWidget(self._create_log_panel())

    def _create_config_panel(self):
        group = QGroupBox("数据源与反馈设置")
        v = QVBoxLayout()

        # 数据源状态
        ds_row = QHBoxLayout()
        self.ds_status = QLabel()
        self.ds_status.setWordWrap(True)
        ds_row.addWidget(self.ds_status, 1)
        go_btn = QPushButton("前往数据源页")
        go_btn.clicked.connect(lambda: self.window().nav_list.setCurrentRow(0))
        ds_row.addWidget(go_btn)
        v.addLayout(ds_row)

        # 模式：教师分析报告 / 学生反馈
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("反馈类型:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("学生反馈（解释评分与提升方向）", "student")
        self.mode_combo.addItem("教师分析报告（班级成绩分析）", "teacher")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        v.addLayout(mode_row)

        # 学生反馈子选项
        self.student_opts = QWidget()
        so = QVBoxLayout(self.student_opts)
        so.setContentsMargins(0, 0, 0, 0)
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("详细度:"))
        self.feedback_type = QComboBox()
        self.feedback_type.addItem("详细反馈")
        self.feedback_type.addItem("简洁反馈")
        r1.addWidget(self.feedback_type)
        r1.addStretch()
        so.addLayout(r1)
        r2 = QHBoxLayout()
        self.include_strengths = QCheckBox("包含亮点")
        self.include_strengths.setChecked(True)
        self.include_weaknesses = QCheckBox("包含失分点")
        self.include_weaknesses.setChecked(True)
        self.include_suggestions = QCheckBox("包含提升建议")
        self.include_suggestions.setChecked(True)
        r2.addWidget(self.include_strengths)
        r2.addWidget(self.include_weaknesses)
        r2.addWidget(self.include_suggestions)
        r2.addStretch()
        so.addLayout(r2)
        v.addWidget(self.student_opts)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.preview_btn = QPushButton("预览")
        self.preview_btn.setMinimumHeight(38)
        self.preview_btn.clicked.connect(self.preview_feedback)
        btn_row.addWidget(self.preview_btn)
        self.generate_btn = QPushButton("批量生成（全部班级）")
        self.generate_btn.setMinimumHeight(38)
        self.generate_btn.setStyleSheet(
            "QPushButton{background-color:#FF9800;color:white;font-weight:bold;"
            "border-radius:5px;padding:8px 16px;}"
            "QPushButton:hover{background-color:#F57C00;}"
            "QPushButton:disabled{background-color:#cccccc;}"
        )
        self.generate_btn.clicked.connect(self.generate_feedback)
        btn_row.addWidget(self.generate_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(38)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_feedback)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        v.addLayout(btn_row)

        # 进度条（生成时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        v.addWidget(self.progress_bar)

        group.setLayout(v)
        return group

    def _on_mode_changed(self):
        is_student = self.mode_combo.currentData() == "student"
        self.student_opts.setVisible(is_student)

    def _create_preview_panel(self):
        group = QGroupBox("预览")
        v = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("选择:"))
        self.student_combo = QComboBox()
        self.student_combo.addItem("点击「预览」加载…")
        row.addWidget(self.student_combo, 1)
        v.addLayout(row)
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setFont(QFont("Microsoft YaHei", 10))
        self.preview_text.setPlaceholderText("点击「预览」查看内容…")
        v.addWidget(self.preview_text)
        group.setLayout(v)
        return group

    def _create_log_panel(self):
        group = QGroupBox("日志输出")
        group.setMaximumHeight(120)
        v = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        v.addWidget(self.log_text)
        group.setLayout(v)
        return group

    # ---------------- 数据源状态 ----------------
    def _refresh_data_source_status(self):
        entries = shared().entries()
        if not entries:
            self.ds_status.setText("⚠ 尚未选择班级压缩包。请到「数据源」页选择（可多选）。")
            self.ds_status.setStyleSheet("color:#c0392b;font-weight:bold;")
            self.generate_btn.setEnabled(False)
            self.preview_btn.setEnabled(False)
        else:
            names = "、".join(e.class_name for e in entries)
            self.ds_status.setText(f"✓ 已选 {len(entries)} 个班级：{names}")
            self.ds_status.setStyleSheet("color:#27ae60;font-weight:bold;")
            self.generate_btn.setEnabled(not self.is_generating)
            self.preview_btn.setEnabled(not self.is_generating)

    def log(self, message):
        if hasattr(self, "log_text"):
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{ts}] {message}")

    def _is_teacher_mode(self) -> bool:
        return self.mode_combo.currentData() == "teacher"

    def _auto_preview(self, *args):
        """选项变化时自动刷新预览（仅学生模式且已加载报告时）。"""
        if self.reports and not self._is_teacher_mode():
            self.preview_feedback()

    # ---------------- 加载 ----------------
    def _load_all_reports(self):
        """跨班级加载所有个人报告：返回 [(report_dict, class_name, experiment_id), ...]。

        复用 class_analysis.load_class_reports，与班级报告对话框共用同一加载器。
        """
        from tools.teaching_management_gui.class_analysis import load_class_reports
        semester = shared().semester()
        reports = []
        for e in shared().entries():
            cls_reports = load_class_reports(e.class_name, e.experiment_id, semester)
            if not cls_reports:
                self.log(f"未找到个人报告（{e.class_name}，请先在「评分」中批阅）")
                continue
            for r in cls_reports:
                reports.append((r, e.class_name, e.experiment_id))
        self.reports = reports
        return reports

    def _populate_student_combo(self, reports):
        self.student_combo.blockSignals(True)
        self.student_combo.clear()
        for rep, cls, _exp in reports:
            self.student_combo.addItem(
                f"[{cls}] {rep.get('name', '?')}({rep.get('student_id', '?')}) - {rep.get('grade', '')}"
            )
        self.student_combo.blockSignals(False)

    def _classes_of(self, reports):
        seen = []
        for _r, cls, exp in reports:
            if (cls, exp) not in seen:
                seen.append((cls, exp))
        return seen

    # ---------------- 预览 ----------------
    def preview_feedback(self):
        if not self._load_all_reports():
            QMessageBox.warning(self, "提示", "未读取到任何个人报告，请先在「评分」中批阅。")
            return
        if self._is_teacher_mode():
            # 预览第一个班级的教师分析报告
            classes = self._classes_of(self.reports)
            cls, exp = classes[0]
            cls_reports = [r for r, c, _e in self.reports if c == cls]
            self._populate_student_combo([(r, c, e) for r, c, e in self.reports])  # 占位
            self.preview_text.setPlainText(build_teacher_report(cls, exp, cls_reports))
            self.log(f"预览教师分析报告：{cls}（共 {len(cls_reports)} 人）")
        else:
            self._populate_student_combo(self.reports)
            idx = max(self.student_combo.currentIndex(), 0)
            rep, cls, exp = self.reports[idx]
            self.preview_text.setPlainText(build_student_feedback(
                rep, cls, exp,
                include_strengths=self.include_strengths.isChecked(),
                include_weaknesses=self.include_weaknesses.isChecked(),
                include_suggestions=self.include_suggestions.isChecked(),
                concise=(self.feedback_type.currentText().startswith("简洁")),
            ))
            self.log(f"预览学生反馈：[{cls}] {rep.get('name', '')}")

    # ---------------- 生成（后台线程）----------------
    def generate_feedback(self):
        if not self._load_all_reports():
            QMessageBox.warning(self, "提示", "未读取到任何个人报告，请先在「评分」中批阅。")
            return
        self.is_generating = True
        self.generate_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)

        mode = "teacher" if self._is_teacher_mode() else "student"
        self.feedback_worker = FeedbackWorker(
            mode=mode,
            reports=self.reports,
            semester=shared().semester(),
            include_strengths=self.include_strengths.isChecked(),
            include_weaknesses=self.include_weaknesses.isChecked(),
            include_suggestions=self.include_suggestions.isChecked(),
            concise=self.feedback_type.currentText().startswith("简洁"),
        )
        self.feedback_worker.log_message.connect(self.log)
        self.feedback_worker.progress.connect(self.on_feedback_progress)
        self.feedback_worker.feedback_completed.connect(self.on_feedback_completed)
        self.feedback_worker.feedback_failed.connect(self.on_feedback_failed)
        self.feedback_worker.feedback_cancelled.connect(self.on_feedback_cancelled)
        self.feedback_worker.start()

    def cancel_feedback(self):
        if self.feedback_worker and self.feedback_worker.isRunning():
            self.feedback_worker.cancel()

    def on_feedback_progress(self, current, total):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)

    def _finish_generation(self):
        self.is_generating = False
        self.generate_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.feedback_worker = None
        self._refresh_data_source_status()

    def on_feedback_completed(self, success, total):
        self._finish_generation()
        self.log(f"生成完成：{success}/{total}")
        QMessageBox.information(self, "完成", f"已生成 {success} 份反馈/报告")

    def on_feedback_failed(self, message):
        self._finish_generation()
        self.log(f"生成失败: {message}")
        QMessageBox.critical(self, "错误", f"生成失败:\n{message}")

    def on_feedback_cancelled(self):
        self._finish_generation()
        self.log("已取消反馈生成")

    def export_report(self):
        """供主窗口「导出报告」菜单调用。"""
        self.generate_feedback()
