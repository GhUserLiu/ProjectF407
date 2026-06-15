#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量评分并行化模块
Parallel Batch Grading

利用多进程加速批量评分，特别适合大规模班级
"""

import os
import sys
import platform
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import time


# Windows多进程兼容
if platform.system() == 'Windows' and __name__ == '__main__':
    # Windows需要spawn方式
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)


@dataclass
class ParallelGradingConfig:
    """并行评分配置"""
    max_workers: int = None  # 最大工作进程数，None表示自动
    chunk_size: int = 4      # 每个进程处理的任务数


@dataclass
class ParallelGradingResult:
    """并行评分结果"""
    results: List[dict]
    total_time: float
    worker_count: int
    speedup: float


def _grade_single_student(args: tuple) -> dict:
    """
    评分单个学生（工作进程函数）

    Args:
        args: (student_id, submission_data, config_dict)

    Returns:
        评分结果
    """
    student_id, submission_data, config_dict = args

    try:
        # 在子进程中导入评分模块
        from tools.plagiarism.grading import batch_grade_with_plagiarism_check

        # 准备提交数据
        submissions = {student_id: submission_data}

        # 执行评分
        results = batch_grade_with_plagiarism_check(
            submissions=submissions,
            rubric=config_dict.get('rubric'),
            experiment_type=config_dict.get('experiment_type', '档位实验'),
            enable_plagiarism_check=config_dict.get('enable_plagiarism_check', True),
            group_info=config_dict.get('group_info')
        )

        if results:
            result = results[0]
            return {
                'student_id': student_id,
                'name': result.name,
                'total_score': result.total_score,
                'percentage': result.percentage,
                'grade': result.grade,
                'plagiarism_info': {
                    'max_similarity': result.plagiarism_info.max_similarity,
                    'similar_to': result.plagiarism_info.similar_to,
                    'penalty_applied': result.plagiarism_info.penalty_applied,
                    'risk_level': result.plagiarism_info.risk_level
                } if hasattr(result, 'plagiarism_info') else None,
                'success': True
            }
        else:
            return {
                'student_id': student_id,
                'success': False,
                'error': 'No result returned'
            }

    except Exception as e:
        return {
            'student_id': student_id,
            'success': False,
            'error': str(e)
        }


class ParallelGradingSystem:
    """并行评分系统"""

    def __init__(self, config: ParallelGradingConfig = None):
        """
        初始化系统

        Args:
            config: 并行配置
        """
        self.config = config or ParallelGradingConfig()

        # 确定工作进程数
        if self.config.max_workers is None:
            # 保留2个核心给系统
            self.config.max_workers = max(2, cpu_count() - 2)
            # 最多使用8个工作进程（避免过度并行）
            self.config.max_workers = min(8, self.config.max_workers)

    def grade_parallel(
        self,
        submissions: Dict[str, Dict],
        rubric: dict,
        experiment_type: str = '档位实验',
        enable_plagiarism_check: bool = True,
        group_info: Dict[str, str] = None,
        progress_callback: Callable[[int, int], None] = None
    ) -> ParallelGradingResult:
        """
        并行批量评分

        Args:
            submissions: 提交内容 {学号: {...}}
            rubric: 评分标准
            experiment_type: 实验类型
            enable_plagiarism_check: 是否启用抄袭检测
            group_info: 小组信息
            progress_callback: 进度回调 (completed, total)

        Returns:
            并行评分结果
        """
        start_time = time.time()

        # 准备任务参数
        config_dict = {
            'rubric': rubric,
            'experiment_type': experiment_type,
            'enable_plagiarism_check': enable_plagiarism_check,
            'group_info': group_info or {}
        }

        tasks = [
            (student_id, submission_data, config_dict)
            for student_id, submission_data in submissions.items()
        ]

        results = []
        completed = 0
        total = len(tasks)

        # 执行并行评分
        with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(_grade_single_student, task): task[0]
                for task in tasks
            }

            # 收集结果
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)  # 单个任务60秒超时
                    results.append(result)
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, total)

                except Exception as e:
                    student_id = futures[future]
                    results.append({
                        'student_id': student_id,
                        'success': False,
                        'error': f'Timeout or error: {str(e)}'
                    })

        elapsed = time.time() - start_time

        # 计算加速比
        # 估算单进程时间（假设每个学生需要2秒）
        estimated_serial_time = len(submissions) * 2.0
        speedup = estimated_serial_time / elapsed if elapsed > 0 else 1.0

        return ParallelGradingResult(
            results=results,
            total_time=elapsed,
            worker_count=self.config.max_workers,
            speedup=speedup
        )


def parallel_grade(
    submissions: Dict[str, Dict],
    rubric: dict,
    experiment_type: str = '档位实验',
    enable_plagiarism_check: bool = True,
    group_info: Dict[str, str] = None,
    max_workers: int = None,
    verbose: bool = True
) -> List[dict]:
    """
    并行批量评分（便捷函数）

    Args:
        submissions: 提交内容
        rubric: 评分标准
        experiment_type: 实验类型
        enable_plagiarism_check: 是否启用抄袭检测
        group_info: 小组信息
        max_workers: 最大工作进程数
        verbose: 是否显示进度

    Returns:
        评分结果列表
    """
    # 配置
    config = ParallelGradingConfig(max_workers=max_workers)
    system = ParallelGradingSystem(config)

    # 进度回调
    def progress_callback(completed, total):
        if verbose:
            print(f"\r进度: {completed}/{total} ({completed/total*100:.1f}%)", end='')

    # 执行评分
    print(f"[并行评分] 使用 {config.max_workers} 个工作进程")
    print(f"[并行评分] 开始评分 {len(submissions)} 个学生...")

    result = system.grade_parallel(
        submissions=submissions,
        rubric=rubric,
        experiment_type=experiment_type,
        enable_plagiarism_check=enable_plagiarism_check,
        group_info=group_info,
        progress_callback=progress_callback
    )

    if verbose:
        print()  # 换行
        print(f"[并行评分] 完成! 耗时: {result.total_time:.1f}秒")
        print(f"[并行评分] 加速比: {result.speedup:.1f}x")

    return result.results


def estimate_performance(student_count: int, worker_count: int = None) -> dict:
    """
    估算并行评分性能

    Args:
        student_count: 学生数量
        worker_count: 工作进程数

    Returns:
        性能估算
    """
    if worker_count is None:
        worker_count = min(8, cpu_count() - 2)

    # 假设每个学生需要2秒评分时间
    serial_time = student_count * 2.0

    # 并行时间（考虑开销）
    parallel_time = (student_count / worker_count) * 2.0 + 5  # +5秒进程启动开销

    speedup = serial_time / parallel_time if parallel_time > 0 else 1.0

    return {
        'student_count': student_count,
        'worker_count': worker_count,
        'serial_time': serial_time,
        'parallel_time': parallel_time,
        'speedup': speedup,
        'time_saved': serial_time - parallel_time
    }


# Windows 兼容：必须在 if __name__ == '__main__': 中使用
if __name__ == '__main__':
    print("批量评分并行化模块测试")
    print("=" * 60)

    # 显示系统信息
    print(f"CPU核心数: {cpu_count()}")
    print(f"建议工作进程数: {min(8, cpu_count() - 2)}")
    print()

    # 性能估算
    test_scenarios = [20, 40, 60, 80]

    print("性能预估:")
    print(f"{'学生数':<10} {'单进程时间':<15} {'并行时间':<15} {'加速比':<10}")
    print("-" * 60)

    for count in test_scenarios:
        perf = estimate_performance(count)
        print(f"{perf['student_count']:<10} "
              f"{perf['serial_time']:<15.1f} "
              f"{perf['parallel_time']:<15.1f} "
              f"{perf['speedup']:<10.1f}x")
