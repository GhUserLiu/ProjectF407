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


class GradingWorker(QThread):
    """批阅工作线程"""

    # 定义信号
    stage_started = pyqtSignal(str, str)  # (stage_id, stage_name)
    stage_progress = pyqtSignal(str, int, int)  # (stage_id, current, total)
    stage_completed = pyqtSignal(str)  # (stage_id)
    error_occurred = pyqtSignal(str)  # (error_message)
    log_message = pyqtSignal(str)  # (message)
    grading_completed = pyqtSignal(object)  # (PipelineResult)
    grading_failed = pyqtSignal(str)  # (error_message)

    def __init__(
        self,
        zip_path: Path,
        class_name: str,
        experiment_id: str,
        config: Optional[AutoGradingConfig] = None,
        skip_organization: bool = False
    ):
        """
        初始化工作线程

        Args:
            zip_path: 班级压缩包路径
            class_name: 班级名称
            experiment_id: 实验ID
            config: 配置对象
            skip_organization: 是否跳过整理阶段
        """
        super().__init__()
        self.zip_path = Path(zip_path)
        self.class_name = class_name
        self.experiment_id = experiment_id
        self.config = config or AutoGradingConfig()
        self.skip_organization = skip_organization
        self.is_cancelled = False

    def run(self):
        """运行批阅任务"""
        try:
            self.log_message.emit("开始批阅...")
            self.log_message.emit(f"班级: {self.class_name}")
            self.log_message.emit(f"实验: {self.experiment_id}")
            self.log_message.emit(f"压缩包: {self.zip_path.name}")

            # 检查文件是否存在
            if not self.zip_path.exists():
                raise FileNotFoundError(f"压缩包不存在: {self.zip_path}")

            # 创建门面（使用信号包装）
            facade = ObservableFacade(
                self.config,
                self.stage_started,
                self.stage_progress,
                self.stage_completed,
                self.log_message,
                lambda: self.is_cancelled
            )

            # 执行批阅
            result = facade.run_full_pipeline(
                self.zip_path,
                self.class_name,
                self.experiment_id,
                self.skip_organization
            )

            # 发送完成信号
            self.grading_completed.emit(result)

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

    def _save_reports(self, pipeline_result, class_report):
        """保存报告（调用facade的方法）"""
        # 使用facade的保存方法
        output_dir = self.config.get_output_dir(
            pipeline_result.class_name,
            pipeline_result.experiment_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        # 保存班级报告
        import json
        report_path = output_dir / "班级报告.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(class_report, f, ensure_ascii=False, indent=2)

        # 保存个人报告
        individuals_dir = output_dir / "个人报告"
        individuals_dir.mkdir(exist_ok=True)

        for grading_result in pipeline_result.grading_results:
            filename = f"{grading_result.student_id}-{grading_result.name}-评分.json"
            individual_path = individuals_dir / filename

            individual_report = {
                'student_id': grading_result.student_id,
                'name': grading_result.name,
                'class_name': grading_result.class_name,
                'total_score': grading_result.total_score,
                'max_score': grading_result.max_score,
                'grade': grading_result.grade,
                'category_scores': [
                    {
                        'category_id': cs.category_id,
                        'category_name': cs.category_name,
                        'max_points': cs.max_points,
                        'earned_points': cs.earned_points,
                    }
                    for cs in grading_result.category_scores
                ],
                'strengths': grading_result.strengths,
                'weaknesses': grading_result.weaknesses,
                'suggestions': grading_result.suggestions,
                'graded_at': grading_result.graded_at.isoformat()
            }

            with open(individual_path, 'w', encoding='utf-8') as f:
                json.dump(individual_report, f, ensure_ascii=False, indent=2)
