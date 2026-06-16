#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化批阅系统
Auto Grading System for STM32 Teaching Projects

提供统一的自动化批阅功能，包括：
- 编译检查
- 代码质量分析
- 报告评分
- 综合反馈生成

主要组件：
- BuildChecker: 编译检查器
- SubmissionProcessor: 提交处理器
- AutoGradingEngine: 整合评分引擎
- AutoGradingFacade: 统一入口
"""

from .config import AutoGradingConfig
from .submission_organizer import SubmissionOrganizer, OrganizationResult, StudentInfo
from .build_checker import BuildChecker, BuildResult, BuildStatus
from .submission_processor import SubmissionProcessor, ProcessedSubmission, ProjectInfo
from .grading_engine import AutoGradingEngine, GradingResult, CategoryScore
from .facade import AutoGradingFacade

__all__ = [
    # 配置
    "AutoGradingConfig",
    # 提交整理
    "SubmissionOrganizer",
    "OrganizationResult",
    "StudentInfo",
    # 编译检查
    "BuildChecker",
    "BuildResult",
    "BuildStatus",
    # 提交处理
    "SubmissionProcessor",
    "ProcessedSubmission",
    "ProjectInfo",
    # 评分引擎
    "AutoGradingEngine",
    "GradingResult",
    "CategoryScore",
    # 统一入口
    "AutoGradingFacade",
]

__version__ = "1.0.0"
__author__ = "STM32F407 Teaching Team"

__all__ = [
    # 配置
    "AutoGradingConfig",
    # 编译检查
    "BuildChecker",
    "BuildResult",
    "BuildStatus",
    # 提交处理
    "SubmissionProcessor",
    "ProcessedSubmission",
    # 评分引擎
    "AutoGradingEngine",
    "GradingResult",
    # 统一入口
    "AutoGradingFacade",
]
