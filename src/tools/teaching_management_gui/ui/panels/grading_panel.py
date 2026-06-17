#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动评分面板（批量版）
Auto Grading Panel

输入取自「数据源」页（支持多班级），点"开始批阅"对所有已选班级依次执行，
结果合并到一张表（含「班级」列）。
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar,
    QTextEdit, QSplitter, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from tools.auto_grading import AutoGradingConfig
from tools.teaching_management_gui.workers.grading_worker import GradingWorker
from tools.teaching_management_gui.ui.class_report_dialog import ClassReportDialog
from tools.teaching_management_gui.data_source import shared
from tools.teaching_management_gui.path_helper import (
    grading_dir as resolve_grading_dir,
)


class GradingPanel(QWidget):
    """自动评分面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = AutoGradingConfig()
        self.all_results = []          # 跨班级合并的 GradingResult 列表
        self.is_grading = False
        self.grading_worker = None
        self.start_time = None

        self.setup_ui()
        # 订阅数据源变化
        shared().entries_changed.connect(self._refresh_data_source_status)
        self._refresh_data_source_status()

    # ---------------- UI ----------------
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        main_layout.addWidget(self._create_data_source_panel())
        main_layout.addWidget(self._create_progress_panel())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._create_stats_panel())
        splitter.addWidget(self._create_results_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, 1)

        main_layout.addWidget(self._create_log_panel())

    def _create_data_source_panel(self):
        group = QGroupBox("数据源")
        layout = QVBoxLayout()

        row = QHBoxLayout()
        self.ds_status = QLabel()
        self.ds_status.setWordWrap(True)
        row.addWidget(self.ds_status, 1)
        go_btn = QPushButton("前往数据源页")
        go_btn.clicked.connect(self._goto_data_source)
        row.addWidget(go_btn)
        layout.addLayout(row)

        self.start_btn = QPushButton("开始批阅（全部班级）")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton { background-color: #4CAF50; color: white; font-size: 14px;
                font-weight: bold; border-radius: 5px; padding: 8px 16px; }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.start_btn.clicked.connect(self.start_grading)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_grading)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        group.setLayout(layout)
        return group

    def _create_progress_panel(self):
        group = QGroupBox("批阅进度")
        layout = QVBoxLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("总体:"), 0)
        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("%p% (%v/%m)")
        row.addWidget(self.overall_progress, 1)
        layout.addLayout(row)
        self.detail_label = QLabel("等待开始...")
        layout.addWidget(self.detail_label)
        group.setLayout(layout)
        return group

    def _create_stats_panel(self):
        group = QGroupBox("批阅结果")
        layout = QHBoxLayout()

        stats = QVBoxLayout()
        self.total_label = QLabel("总提交: 0")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.avg_label = QLabel("平均分: 0.0")
        self.avg_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.time_label = QLabel("用时: 0:00")
        self.time_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats.addWidget(self.total_label)
        stats.addWidget(self.avg_label)
        stats.addWidget(self.time_label)
        stats.addStretch()
        layout.addLayout(stats, 1)

        btns = QVBoxLayout()
        view_report_btn = QPushButton("查看班级报告")
        view_report_btn.clicked.connect(self.view_class_report)
        btns.addWidget(view_report_btn)
        export_btn = QPushButton("导出个人报告")
        export_btn.clicked.connect(self.export_all_reports)
        btns.addWidget(export_btn)
        btns.addStretch()
        layout.addLayout(btns, 1)

        group.setLayout(layout)
        return group

    def _create_results_panel(self):
        group = QGroupBox("学生列表")
        layout = QVBoxLayout()
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "班级", "学号", "姓名", "编译", "代码", "报告", "总分", "等级"
        ])
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.doubleClicked.connect(self.show_student_detail)
        layout.addWidget(self.results_table)
        group.setLayout(layout)
        return group

    def _create_log_panel(self):
        group = QGroupBox("日志输出")
        group.setMaximumHeight(150)
        layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
        group.setLayout(layout)
        return group

    # ---------------- 数据源状态 ----------------
    def _refresh_data_source_status(self):
        entries = shared().entries()
        if not entries:
            self.ds_status.setText("⚠ 尚未选择班级压缩包。请到「数据源」页选择（可多选）。")
            self.ds_status.setStyleSheet("color:#c0392b;font-weight:bold;")
            self.start_btn.setEnabled(False)
        else:
            names = "、".join(e.class_name for e in entries)
            self.ds_status.setText(f"✓ 已选 {len(entries)} 个班级：{names}")
            self.ds_status.setStyleSheet("color:#27ae60;font-weight:bold;")
            self.start_btn.setEnabled(not self.is_grading)

    def _goto_data_source(self):
        win = self.window()
        if hasattr(win, "nav_list"):
            win.nav_list.setCurrentRow(0)

    # ---------------- 日志 ----------------
    def log(self, message):
        if hasattr(self, "log_text"):
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{ts}] {message}")

    # ---------------- 批量批阅 ----------------
    def start_grading(self):
        entries = shared().entries()
        if not entries:
            QMessageBox.warning(self, "警告", "请先到「数据源」页选择班级压缩包")
            return

        self.is_grading = True
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log_text.clear()
        self.results_table.setRowCount(0)
        self.overall_progress.setValue(0)
        self.detail_label.setText("初始化...")
        self.start_time = datetime.now()
        self.log(f"开始批量批阅：共 {len(entries)} 个班级")

        self.grading_worker = GradingWorker(entries, shared().semester(), self.config)
        self.grading_worker.stage_started.connect(self.on_stage_started)
        self.grading_worker.stage_progress.connect(self.on_stage_progress)
        self.grading_worker.stage_completed.connect(self.on_stage_completed)
        self.grading_worker.log_message.connect(self.log)
        self.grading_worker.grading_completed.connect(self.on_grading_completed)
        self.grading_worker.grading_failed.connect(self.on_grading_failed)
        self.grading_worker.start()

    def on_stage_started(self, stage_id, stage_name):
        self.detail_label.setText(stage_name)

    def on_stage_progress(self, stage_id, current, total):
        if stage_id == "analyze":
            self.overall_progress.setRange(0, total)
            self.overall_progress.setValue(current)

    def on_stage_completed(self, stage_id):
        pass

    def on_grading_completed(self, results):
        self.all_results = results or []
        self.is_grading = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.overall_progress.setValue(self.overall_progress.maximum())
        self.detail_label.setText("批阅完成")

        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.time_label.setText(f"用时: {int(elapsed // 60)}:{int(elapsed % 60):02d}")

        total = len(self.all_results)
        avg = (sum(r.total_score for r in self.all_results) / total) if total else 0
        self.total_label.setText(f"总提交: {total}")
        self.avg_label.setText(f"平均分: {avg:.1f}")
        self._fill_results_table()
        self.log(f"批阅完成！共 {total} 人，平均 {avg:.1f}")

    def on_grading_failed(self, error_message):
        self.is_grading = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.detail_label.setText("批阅失败")
        self.log(f"批阅失败: {error_message}")
        QMessageBox.critical(self, "错误", f"批阅失败:\n{error_message}")

    def _fill_results_table(self):
        results = self.all_results
        self.results_table.setRowCount(len(results))
        for row, r in enumerate(results):
            compilation_score = code_score = report_score = 0
            compilation_ok = True
            for cs in r.category_scores:
                if cs.category_id == "compilation":
                    compilation_score = cs.earned_points
                    compilation_ok = compilation_score > 0
                elif cs.category_id == "code_quality":
                    code_score = cs.earned_points
                elif cs.category_id == "report_quality":
                    report_score = cs.earned_points
            cells = [
                r.class_name, r.student_id, r.name,
                "✓" if compilation_ok else "✗",
                f"{code_score:.0f}", f"{report_score:.0f}",
                f"{r.total_score:.1f}", r.grade,
            ]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(str(val))
                if col == 3:
                    item.setForeground(Qt.GlobalColor.green if compilation_ok else Qt.GlobalColor.red)
                if col == 7:
                    if r.grade == "A":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    elif r.grade == "F":
                        item.setForeground(Qt.GlobalColor.red)
                self.results_table.setItem(row, col, item)

    def cancel_grading(self):
        if self.is_grading:
            if QMessageBox.question(self, "确认", "确定取消批阅？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.is_grading = False
                if self.grading_worker:
                    self.grading_worker.cancel()
                if self.grading_worker and self.grading_worker.isRunning():
                    self.grading_worker.wait(3000)
                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)

    # ---------------- 详情 / 报告 ----------------
    def show_student_detail(self, index):
        row = index.row()
        if row >= len(self.all_results):
            return
        r = self.all_results[row]
        detail = (
            f"<h3>{r.class_name} - {r.name}</h3>"
            f"<table border=1 cellpadding=4>"
            f"<tr><td>学号</td><td>{r.student_id}</td></tr>"
            f"<tr><td>总分</td><td>{r.total_score:.1f}/{r.max_score:.1f}</td></tr>"
            f"<tr><td>等级</td><td><b>{r.grade}</b></td></tr></table>"
        )
        if r.strengths:
            detail += "<br><b>优点:</b><ul>" + "".join(f"<li>{s}</li>" for s in r.strengths) + "</ul>"
        if r.weaknesses:
            detail += "<br><b>不足:</b><ul>" + "".join(f"<li>{s}</li>" for s in r.weaknesses) + "</ul>"
        QMessageBox.information(self, "学生详情", detail)

    def view_class_report(self):
        """打开班级报告对话框（对第一个已选班级）。"""
        entries = shared().entries()
        if not entries:
            QMessageBox.warning(self, "提示", "请先在「数据源」页选择班级")
            return
        e = entries[0]
        report_dir = resolve_grading_dir(e.class_name, e.experiment_id, shared().semester())
        if not report_dir.exists():
            QMessageBox.warning(self, "报告不存在",
                f"未找到 {e.class_name} 的批阅报告：\n{report_dir}\n请先执行批阅。")
            return
        self.log(f"打开班级报告：{e.class_name}（其它班级报告见各自 results/grading/）")
        ClassReportDialog(e.class_name, e.experiment_id, self).exec()

    def export_report(self):
        """供主窗口「导出报告」菜单调用。"""
        self.export_all_reports()

    def export_all_reports(self):
        """把所有已选班级的个人报告导出到一个目录。"""
        entries = shared().entries()
        if not entries:
            QMessageBox.warning(self, "提示", "请先在「数据源」页选择班级")
            return
        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录", str(Path.cwd() / "exports"))
        if not export_dir:
            return
        export_path = Path(export_dir)
        total = success = 0
        for e in entries:
            individuals = resolve_grading_dir(e.class_name, e.experiment_id, shared().semester()) / "个人报告"
            if not individuals.exists():
                continue
            for rf in individuals.glob("*-评分.json"):
                total += 1
                try:
                    (export_path / f"{e.class_name}-{rf.name}").write_text(
                        rf.read_text(encoding="utf-8"), encoding="utf-8")
                    success += 1
                except Exception as ex:
                    self.log(f"导出失败 {rf.name}: {ex}")
        self.log(f"导出完成: {success}/{total}")
        QMessageBox.information(self, "导出完成", f"成功导出 {success}/{total} 个报告\n{export_path}")
