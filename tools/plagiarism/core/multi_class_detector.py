#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多班级查重检测器
Multi-Class Plagiarism Detector

支持同时处理多个班级的查重检测，包括：
1. 班级内检测
2. 跨班级检测
3. 班级对比分析

作者: STM32F407 教学团队
版本: 1.0.0
"""

import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from collections import defaultdict

# 导入核心检测器
from .detector import (
    PlagiarismDetector,
    SimilarityMethod,
    SimilarityResult
)

# 导入工具函数
from tools.submission_utils import get_student_info


@dataclass
class ClassDetectionResult:
    """单个班级的检测结果"""
    class_id: str
    class_name: str
    student_count: int
    suspicious_pairs: int
    all_results: Dict[str, List[SimilarityResult]]
    suspicious_results: List[SimilarityResult]
    groups: List[Dict]

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总信息"""
        return {
            'class_id': self.class_id,
            'class_name': self.class_name,
            'student_count': self.student_count,
            'suspicious_pairs': self.suspicious_pairs,
            'suspicious_rate': self.suspicious_pairs / self.student_count if self.student_count > 0 else 0,
            'group_count': len(self.groups)
        }


@dataclass
class MultiClassDetectionResult:
    """多班级检测结果汇总"""
    class_results: Dict[str, ClassDetectionResult]
    cross_class_results: List[SimilarityResult]
    class_comparisons: List[Dict]
    timestamp: str

    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        total_students = sum(r.student_count for r in self.class_results.values())
        total_suspicious = sum(r.suspicious_pairs for r in self.class_results.values())
        cross_class_count = len(self.cross_class_results)

        return {
            'total_classes': len(self.class_results),
            'total_students': total_students,
            'total_suspicious_pairs': total_suspicious,
            'cross_class_suspicious_pairs': cross_class_count,
            'class_comparisons': len(self.class_comparisons),
            'timestamp': self.timestamp
        }


class MultiClassDetector:
    """多班级查重检测器"""

    def __init__(
        self,
        class_configs: List[Dict],
        threshold: float = 60.0,
        method: SimilarityMethod = SimilarityMethod.HYBRID,
        enable_cross_class: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ):
        """
        初始化多班级检测器

        Args:
            class_configs: 班级配置列表，每项包含 class_id, class_name, submissions_dir
            threshold: 相似度阈值
            method: 相似度计算方法
            enable_cross_class: 是否启用跨班级检测
            progress_callback: 进度回调函数(进度百分比, 状态描述)
        """
        self.class_configs = class_configs
        self.threshold = threshold
        self.method = method
        self.enable_cross_class = enable_cross_class
        self.progress_callback = progress_callback

        # 存储结果
        self.class_results: Dict[str, ClassDetectionResult] = {}
        self.cross_class_results: List[SimilarityResult] = []
        self.class_comparisons: List[Dict] = []

        # 学生提交数据（用于跨班级检测）
        self.all_submissions: Dict[str, Dict] = {}
        self.student_class_mapping: Dict[str, str] = {}  # student_id -> class_id

    def _report_progress(self, progress: int, message: str):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(progress, message)

    def detect_all(self) -> MultiClassDetectionResult:
        """
        执行多班级查重检测

        Returns:
            MultiClassDetectionResult: 多班级检测结果
        """
        start_time = datetime.now()

        # 阶段1: 加载所有班级的提交
        self._load_all_submissions()
        self._report_progress(10, "学生提交加载完成")

        # 阶段2: 班级内检测
        self._detect_within_classes()
        self._report_progress(50, "班级内检测完成")

        # 阶段3: 跨班级检测
        if self.enable_cross_class:
            self._detect_cross_classes()
            self._report_progress(80, "跨班级检测完成")

        # 阶段4: 班级对比分析
        self._compare_classes()
        self._report_progress(95, "班级对比分析完成")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        self._report_progress(100, f"检测完成，耗时 {duration:.1f} 秒")

        return MultiClassDetectionResult(
            class_results=self.class_results,
            cross_class_results=self.cross_class_results,
            class_comparisons=self.class_comparisons,
            timestamp=end_time.isoformat()
        )

    def _load_all_submissions(self):
        """加载所有班级的提交"""
        self.all_submissions = {}
        self.student_class_mapping = {}

        total_classes = len(self.class_configs)

        for idx, config in enumerate(self.class_configs):
            class_id = config['class_id']
            class_name = config['class_name']
            submissions_dir = Path(config['submissions_dir'])

            self._report_progress(
                int((idx / total_classes) * 10),
                f"加载 {class_name} 提交..."
            )

            # 提取学生信息
            student_info = get_student_info(submissions_dir)

            # 存储提交并记录班级映射
            for student_id, info in student_info.items():
                content = info.get('content', '')
                # 只保存有内容的学生提交
                if content:
                    # 添加班级前缀避免学号冲突
                    prefixed_id = f"{class_id}_{student_id}"
                    self.all_submissions[prefixed_id] = {
                        'name': info.get('name', ''),
                        'text': content,
                        'original_id': student_id,
                        'class_id': class_id
                    }
                    self.student_class_mapping[prefixed_id] = class_id

            # 更新班级配置中的学生数量
            config['student_count'] = len([s for s in self.all_submissions.values() if s['class_id'] == class_id])

    def _detect_within_classes(self):
        """执行班级内检测"""
        total_classes = len(self.class_configs)

        for idx, config in enumerate(self.class_configs):
            class_id = config['class_id']
            class_name = config['class_name']

            progress = 10 + int((idx / total_classes) * 40)
            self._report_progress(progress, f"检测 {class_name}...")

            # 收集该班级的提交
            class_submissions = {}
            for prefixed_id, submission in self.all_submissions.items():
                if submission['class_id'] == class_id and submission.get('text'):
                    # 使用原始学号作为键
                    original_id = submission['original_id']
                    class_submissions[original_id] = {
                        'name': submission['name'],
                        'text': submission['text']
                    }

            if not class_submissions:
                self.class_results[class_id] = ClassDetectionResult(
                    class_id=class_id,
                    class_name=class_name,
                    student_count=0,
                    suspicious_pairs=0,
                    all_results={},
                    suspicious_results=[],
                    groups=[]
                )
                continue

            # 创建检测器并执行检测
            detector = PlagiarismDetector(
                method=self.method,
                threshold=self.threshold
            )

            all_results, suspicious, _ = detector.detect(class_submissions)

            # 检测抄袭团伙
            groups = detector.detect_groups(suspicious)

            # 存储结果
            self.class_results[class_id] = ClassDetectionResult(
                class_id=class_id,
                class_name=class_name,
                student_count=len(class_submissions),
                suspicious_pairs=len(suspicious),
                all_results=all_results,
                suspicious_results=suspicious,
                groups=groups
            )

    def _detect_cross_classes(self):
        """执行跨班级检测"""
        self._report_progress(50, "开始跨班级检测...")

        if len(self.all_submissions) < 2:
            return

        # 创建全局检测器
        global_detector = PlagiarismDetector(
            method=self.method,
            threshold=self.threshold
        )

        # 执行全局检测
        all_results, suspicious, _ = global_detector.detect(self.all_submissions)

        # 过滤真正的跨班级结果
        for result in suspicious:
            class1 = self.student_class_mapping.get(result.student_id)
            class2 = self.student_class_mapping.get(result.similar_to)

            # 只保留跨班级的结果
            if class1 and class2 and class1 != class2:
                # 添加班级元数据
                result.metadata = result.metadata or {}
                result.metadata['class_id_1'] = class1
                result.metadata['class_id_2'] = class2
                result.metadata['class_name_1'] = self._get_class_name(class1)
                result.metadata['class_name_2'] = self._get_class_name(class2)
                result.metadata['is_cross_class'] = True

                # 使用原始学号
                original_id1 = self.all_submissions[result.student_id]['original_id']
                original_id2 = self.all_submissions[result.similar_to]['original_id']

                # 创建新的结果对象（使用原始学号）
                cross_result = SimilarityResult(
                    student_id=original_id1,
                    similar_to=original_id2,
                    overall_similarity=result.overall_similarity,
                    text_similarity=result.text_similarity,
                    code_similarity=result.code_similarity,
                    structure_similarity=result.structure_similarity,
                    method=result.method,
                    is_cross_group=True,
                    is_suspicious=result.is_suspicious,
                    metadata=result.metadata
                )

                self.cross_class_results.append(cross_result)

        self._report_progress(80, f"跨班级检测完成，发现 {len(self.cross_class_results)} 对跨班级相似")

    def _get_class_name(self, class_id: str) -> str:
        """获取班级名称"""
        for config in self.class_configs:
            if config['class_id'] == class_id:
                return config['class_name']
        return class_id

    def _compare_classes(self) -> List[Dict]:
        """执行班级对比分析"""
        self.class_comparisons = []

        class_ids = list(self.class_results.keys())

        for i in range(len(class_ids)):
            for j in range(i + 1, len(class_ids)):
                class1_id = class_ids[i]
                class2_id = class_ids[j]

                result1 = self.class_results[class1_id]
                result2 = self.class_results[class2_id]

                # 计算跨班级指标
                cross_pairs = [
                    r for r in self.cross_class_results
                    if r.metadata.get('class_id_1') == class1_id and
                       r.metadata.get('class_id_2') == class2_id
                ]

                # 双向统计（包括反向的）
                cross_pairs_reverse = [
                    r for r in self.cross_class_results
                    if r.metadata.get('class_id_1') == class2_id and
                       r.metadata.get('class_id_2') == class1_id
                ]

                all_cross_pairs = cross_pairs + cross_pairs_reverse

                avg_sim = sum(r.overall_similarity for r in all_cross_pairs) / len(all_cross_pairs) if all_cross_pairs else 0
                max_sim = max(r.overall_similarity for r in all_cross_pairs) if all_cross_pairs else 0

                comparison = {
                    'class_id_1': class1_id,
                    'class_name_1': result1.class_name,
                    'class_id_2': class2_id,
                    'class_name_2': result2.class_name,
                    'avg_similarity': round(avg_sim, 1),
                    'max_similarity': round(max_sim, 1),
                    'suspicious_pairs': len(all_cross_pairs),
                    'cross_class_pairs': len(all_cross_pairs),
                    'avg_score_diff': 0.0,  # 可从评分结果计算
                    'submission_rate_diff': 0.0,  # 可从提交率计算
                    'compared_at': datetime.now().isoformat()
                }

                self.class_comparisons.append(comparison)

        return self.class_comparisons

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        summary = {
            'total_classes': len(self.class_configs),
            'total_students': sum(c.get('student_count', 0) for c in self.class_configs),
            'classes': []
        }

        for class_id, result in self.class_results.items():
            summary['classes'].append({
                'class_id': class_id,
                'class_name': result.class_name,
                'student_count': result.student_count,
                'suspicious_pairs': result.suspicious_pairs,
                'suspicious_rate': result.suspicious_pairs / result.student_count if result.student_count > 0 else 0,
                'group_count': len(result.groups)
            })

        summary['cross_class_pairs'] = len(self.cross_class_results)
        summary['class_comparisons'] = len(self.class_comparisons)

        return summary


def create_multi_class_config(
    base_dir: Path,
    semester: str = "2026-春季",
    experiment: str = "07-car-gear",
    class_pattern: str = "*班"
) -> List[Dict]:
    """
    自动创建多班级配置

    Args:
        base_dir: 基础目录
        semester: 学期
        experiment: 实验编号
        class_pattern: 班级名称模式

    Returns:
        班级配置列表
    """
    configs = []

    # 扫描班级目录
    semester_dir = base_dir / "docs/teaching" / semester

    if not semester_dir.exists():
        return configs

    for class_dir in semester_dir.glob(class_pattern):
        experiment_dir = class_dir / experiment

        if not experiment_dir.exists():
            continue

        submissions_dir = experiment_dir / "submissions" / "extracted"

        if not submissions_dir.exists():
            continue

        # 创建班级配置
        class_id = f"{semester}_{class_dir.name}"
        configs.append({
            'class_id': class_id,
            'class_name': class_dir.name,
            'submissions_dir': str(submissions_dir),
            'experiment_dir': str(experiment_dir),
            'student_count': 0  # 将在加载时更新
        })

    return configs
