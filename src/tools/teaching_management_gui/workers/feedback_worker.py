#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
反馈生成工作线程
Feedback Generation Worker Thread

把原先在 GUI 线程同步执行的「批量生成学生反馈 / 教师分析报告」（每个学生/班级
都要写 .md + .docx）移到后台线程，避免大批量时界面冻结。
"""

import sys
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.teaching_management_gui.feedback_reports import (  # noqa: E402
    build_student_feedback,
    build_teacher_report,
)
from tools.teaching_management_gui.path_helper import (  # noqa: E402
    feedback_dir as resolve_feedback_dir,
)

try:  # noqa: E402
    from docx import Document as _DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


def _write_docx(path: Path, title: str, text: str):
    """把多行文本写成 Word（标题 + 列表/段落）。"""
    doc = _DocxDocument()
    doc.add_heading(title, level=1)
    for line in text.splitlines():
        if line.startswith("# "):
            continue  # 主标题已加
        if line.startswith("## "):
            doc.add_heading(line[3:].strip(), level=2)
        elif line.startswith("| "):
            doc.add_paragraph(line)  # 表格行按段落保留
        elif line.startswith("- "):
            doc.add_paragraph(line[2:], style="List Bullet")
        elif line.strip():
            doc.add_paragraph(line)
    doc.save(path)


class FeedbackWorker(QThread):
    """批量反馈/报告生成线程。

    输入与 FeedbackPanel.generate_feedback 收集的一致；在 run() 内完成全部文件写入，
    通过信号回报进度/日志/结果，GUI 线程不参与磁盘与 docx 渲染。
    """

    log_message = pyqtSignal(str)
    progress = pyqtSignal(int, int)            # (current, total)
    feedback_completed = pyqtSignal(int, int)  # (success, total)
    feedback_failed = pyqtSignal(str)
    feedback_cancelled = pyqtSignal()

    def __init__(
        self,
        mode: str,
        reports,
        semester: str,
        include_strengths: bool = True,
        include_weaknesses: bool = True,
        include_suggestions: bool = True,
        concise: bool = False,
    ):
        super().__init__()
        self.mode = mode  # "student" | "teacher"
        self.reports = list(reports)
        self.semester = semester
        self.include_strengths = include_strengths
        self.include_weaknesses = include_weaknesses
        self.include_suggestions = include_suggestions
        self.concise = concise
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True
        self.log_message.emit("正在取消...")

    def run(self):
        try:
            if not HAS_DOCX:
                self.log_message.emit("提示：未安装 python-docx，仅生成 Markdown。")

            if self.mode == "teacher":
                success, total = self._generate_teacher()
            else:
                success, total = self._generate_student()

            if self.is_cancelled:
                self.log_message.emit(f"反馈生成已取消（已完成 {success}/{total}）")
                self.feedback_cancelled.emit()
            else:
                self.feedback_completed.emit(success, total)
        except Exception as e:
            self.feedback_failed.emit(str(e))

    # ---------------- 学生反馈 ----------------
    def _generate_student(self):
        total = len(self.reports)
        success = 0
        self.log_message.emit(f"批量生成学生反馈：{total} 名学生")
        for i, (rep, cls, exp) in enumerate(self.reports):
            if self.is_cancelled:
                break
            self.progress.emit(i, total)
            try:
                text = build_student_feedback(
                    rep, cls, exp,
                    self.include_strengths, self.include_weaknesses,
                    self.include_suggestions, self.concise,
                )
                out_dir = resolve_feedback_dir(cls, exp, self.semester) / "学生反馈"
                out_dir.mkdir(parents=True, exist_ok=True)
                sid = rep.get("student_id", "unknown")
                name = rep.get("name", "")
                base = f"{sid}_{name}_反馈" if name else f"{sid}_反馈"
                (out_dir / f"{base}.md").write_text(text, encoding="utf-8")
                if HAS_DOCX:
                    _write_docx(out_dir / f"{base}.docx", f"{name or sid} 实验反馈", text)
                success += 1
            except Exception as e:
                self.log_message.emit(f"生成失败 {rep.get('name', '')}: {e}")
        self.progress.emit(total, total)
        if not self.is_cancelled:
            self.log_message.emit(f"学生反馈完成：{success}/{total}")
        return success, total

    # ---------------- 教师分析报告 ----------------
    def _generate_teacher(self):
        # 按 (class, exp) 去重保序
        classes = []
        for _r, cls, exp in self.reports:
            if (cls, exp) not in classes:
                classes.append((cls, exp))
        total = len(classes)
        success = 0
        self.log_message.emit(f"批量生成教师分析报告：{total} 个班级")
        for i, (cls, exp) in enumerate(classes):
            if self.is_cancelled:
                break
            self.progress.emit(i, total)
            cls_reports = [r for r, c, _e in self.reports if c == cls]
            if not cls_reports:
                continue
            try:
                text = build_teacher_report(cls, exp, cls_reports)
                out_dir = resolve_feedback_dir(cls, exp, self.semester) / "教师报告"
                out_dir.mkdir(parents=True, exist_ok=True)
                base = f"{cls}_{exp}_教师分析报告"
                (out_dir / f"{base}.md").write_text(text, encoding="utf-8")
                if HAS_DOCX:
                    _write_docx(out_dir / f"{base}.docx", f"{cls} 教学分析报告", text)
                success += 1
                self.log_message.emit(f"  {cls}：已生成（{len(cls_reports)} 人）")
            except Exception as e:
                self.log_message.emit(f"  {cls} 生成失败: {e}")
        self.progress.emit(total, total)
        if not self.is_cancelled:
            self.log_message.emit(f"教师分析报告完成：{success}/{total}")
        return success, total
