#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批阅工作线程
Grading Worker Thread

在后台线程中执行批阅任务，避免阻塞GUI。
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.auto_grading import AutoGradingFacade, AutoGradingConfig
from tools.auto_grading.facade import PipelineResult
from tools.teaching_management_gui.data_source import ClassEntry


class GradingWorker(QThread):
    """批阅工作线程（批量：遍历多个班级条目）"""

    # 定义信号
    stage_started = pyqtSignal(str, str)  # (stage_id, stage_name)
    stage_progress = pyqtSignal(str, int, int)  # (stage_id, current, total)
    stage_completed = pyqtSignal(str)  # (stage_id)
    error_occurred = pyqtSignal(str)  # (error_message)
    log_message = pyqtSignal(str)  # (message)
    grading_completed = pyqtSignal(object)  # (list[GradingResult]，跨班级合并)
    grading_cancelled = pyqtSignal()  # 取消：不发部分结果，避免被面板当成"完成"
    grading_failed = pyqtSignal(str)  # (error_message)

    def __init__(
        self,
        entries,
        semester: str = "2026-春季",
        config: Optional[AutoGradingConfig] = None,
    ):
        """
        初始化批量批阅工作线程

        Args:
            entries: ClassEntry 列表（班级/实验/压缩包）
            semester: 学期（决定产物路径）
            config: 配置对象
        """
        super().__init__()
        self.entries = list(entries)
        self.semester = semester
        self.config = config or AutoGradingConfig()
        self.config.semester = semester
        self.is_cancelled = False

    def run(self):
        """对每个班级条目依次执行批阅，合并所有 GradingResult。"""
        try:
            all_results = []
            total = len(self.entries)
            self.log_message.emit(f"开始批量批阅：共 {total} 个班级")

            for i, entry in enumerate(self.entries):
                if self.is_cancelled:
                    break
                zip_path = Path(entry.zip_path)
                self.log_message.emit(
                    f"({i + 1}/{total}) 班级 {entry.class_name} / 实验 {entry.experiment_id}"
                )
                self.log_message.emit(f"压缩包: {zip_path.name}")

                if not zip_path.exists():
                    self.log_message.emit(f"警告: 压缩包不存在，跳过: {zip_path}")
                    self.stage_progress.emit("analyze", i + 1, total)
                    continue

                # 每个班级一个可观察门面，复用其 run_full_pipeline
                facade = ObservableFacade(
                    self.config,
                    self.stage_started,
                    self.stage_progress,
                    self.stage_completed,
                    self.log_message,
                    lambda: self.is_cancelled,
                )
                result = facade.run_full_pipeline(
                    zip_path,
                    entry.class_name,
                    entry.experiment_id,
                    False,
                )
                all_results.extend(result.grading_results)
                self.stage_progress.emit("analyze", i + 1, total)

            # 取消时不发 grading_completed（避免部分结果被当成"完成"），改发取消信号
            if self.is_cancelled:
                self.log_message.emit(f"批阅已取消（已丢弃 {len(all_results)} 条部分结果）")
                self.grading_cancelled.emit()
            else:
                self.grading_completed.emit(all_results)

        except Exception as e:
            self.error_occurred.emit(str(e))
            self.grading_failed.emit(str(e))

    def cancel(self):
        """取消批阅"""
        self.is_cancelled = True
        self.log_message.emit("正在取消...")


class ObservableFacade:
    """可观察的门面（用于向GUI发送信号）"""

    def __init__(
        self,
        config: AutoGradingConfig,
        stage_started_sig,
        stage_progress_sig,
        stage_completed_sig,
        log_message_sig,
        is_cancelled_func
    ):
        """
        初始化

        Args:
            config: 配置对象
            stage_started_sig: 阶段开始信号
            stage_progress_sig: 阶段进度信号
            stage_completed_sig: 阶段完成信号
            log_message_sig: 日志消息信号
            is_cancelled_func: 检查是否取消的函数
        """
        self.config = config
        self.stage_started = stage_started_sig
        self.stage_progress = stage_progress_sig
        self.stage_completed = stage_completed_sig
        self.log_message = log_message_sig
        self.is_cancelled = is_cancelled_func

        # 创建实际的门面
        self.facade = AutoGradingFacade(config)

    def run_full_pipeline(
        self,
        class_zip: Path,
        class_name: str,
        experiment_id: str,
        skip_organization: bool = False
    ) -> PipelineResult:
        """运行完整流水线（带信号通知）"""
        result = PipelineResult(
            class_name=class_name,
            experiment_id=experiment_id
        )

        self.log_message.emit("=" * 70)
        self.log_message.emit("自动化批阅系统")
        self.log_message.emit("=" * 70)

        # 阶段1: 整理提交格式
        if not skip_organization:
            self.log_message.emit("阶段1: 整理提交格式")
            self.stage_started.emit("organize", "整理提交")

            # 模拟进度（因为没有细粒度进度）
            self.stage_progress.emit("organize", 1, 10)
            org_result = self.facade.organizer.process_class_submission(
                class_zip,
                class_name,
                experiment_id
            )
            self.stage_progress.emit("organize", 10, 10)
            self.stage_completed.emit("organize")

            result.organization_result = org_result

            self.log_message.emit(f"  成功: {org_result.successful}/{org_result.total_students}")

            if org_result.total_students == 0:
                self.log_message.emit("警告: 没有找到学生提交")
                return result

            if self.is_cancelled():
                return result
        else:
            self.log_message.emit("阶段1: 跳过（已整理）")

        # 阶段2: 处理提交数据
        self.log_message.emit("阶段2: 处理提交数据")
        self.stage_started.emit("compile", "编译检查")  # 使用compile stage_id
        self.stage_progress.emit("compile", 1, 10)

        submissions = self.facade.processor.process_class_submissions(
            class_name,
            experiment_id
        )

        self.stage_progress.emit("compile", 10, 10)
        self.stage_completed.emit("compile")

        result.total_submissions = len(submissions)
        self.log_message.emit(f"  处理完成: {len(submissions)} 个提交")

        if not submissions:
            self.log_message.emit("警告: 没有找到提交数据")
            return result

        # 阶段3: 批量评分
        self.log_message.emit("阶段3: 批量评分")
        self.stage_started.emit("analyze", "代码分析")  # 使用analyze stage_id

        grading_results = []
        total = len(submissions)

        for i, submission in enumerate(submissions):
            if self.is_cancelled():
                break

            self.log_message.emit(f"评分 ({i+1}/{total}): {submission.student_id}-{submission.name}")
            self.stage_progress.emit("analyze", i + 1, total)

            grading_result = self.facade.engine.grade_submission(submission)
            grading_results.append(grading_result)

            self.log_message.emit(f"  得分: {grading_result.total_score:.1f}/{grading_result.max_score:.1f} ({grading_result.grade})")

        self.stage_progress.emit("analyze", total, total)
        self.stage_completed.emit("analyze")

        result.grading_results = grading_results
        result.successful_graded = len(grading_results)

        # 阶段4: 生成报告
        self.log_message.emit("阶段4: 生成报告")
        self.stage_started.emit("grade", "报告评分")  # 使用grade stage_id
        self.stage_progress.emit("grade", 1, 10)

        if grading_results:
            class_report = self.facade.engine.generate_class_report(grading_results)
            self.facade._save_reports(result, class_report)
            self.log_message.emit(f"  班级报告已生成")
            self.log_message.emit(f"  个人报告已生成")
            self.stage_progress.emit("grade", 10, 10)

        self.stage_completed.emit("grade")

        result.completed_at = datetime.now()

        self.log_message.emit("=" * 70)
        self.log_message.emit("批阅完成！")

        if grading_results:
            avg_score = sum(r.total_score for r in grading_results) / len(grading_results)
            self.log_message.emit(f"平均分: {avg_score:.1f}")

        return result

