#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生端共享状态
Shared Submission State

集中管理学生端「选中的报告 + 源码 + 身份 + 实验 + 上次自检结果」，
供「我的作业 / 提交检测 / 自评结果」三个面板统一取用。

通过模块级单例 shared() 访问；状态变更通过 Qt 信号通知各面板刷新。
镜像教师端 tools.teaching_management_gui.data_source 的设计。
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .qt_compat import QObject, pyqtSignal

from .id_card import StudentIdentity


class SourceKind(str, Enum):
    """源代码输入类型。"""
    NONE = "none"
    DIRECTORY = "directory"
    ZIP = "zip"
    SEVEN_ZIP = "7z"


@dataclass
class SubmissionState:
    """学生端当前状态。"""
    report_path: Optional[Path] = None
    source_path: Optional[Path] = None
    source_kind: SourceKind = SourceKind.NONE
    identity: StudentIdentity = field(default_factory=StudentIdentity)
    experiment_code: str = ""           # 如 "07-car-gear"
    last_result: object = None          # SelfCheckResult 缓存，便于面板间切换


class SubmissionStateManager(QObject):
    """状态管理器（单例）。

    持有当前选中的报告/源码/身份/实验及上次结果；变更时发射 state_changed，
    供各面板刷新。
    """

    state_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._state = SubmissionState()

    def state(self) -> SubmissionState:
        return self._state

    def update(self, **kwargs) -> None:
        """合并更新字段；仅当值真正变化时发射信号。"""
        changed = False
        for k, v in kwargs.items():
            if hasattr(self._state, k) and getattr(self._state, k) != v:
                setattr(self._state, k, v)
                changed = True
        if changed:
            self.state_changed.emit()

    def set_result(self, result: object) -> None:
        """缓存最近一次自检结果并通知面板。"""
        self._state.last_result = result
        self.state_changed.emit()

    def is_runnable(self) -> bool:
        """是否满足「开始检测」条件：报告存在 + 身份完整 + 已选实验。

        源码可选——缺源码会丢编译/代码质量分，但检测与自评仍有意义。
        """
        s = self._state
        return (
            bool(s.report_path and Path(s.report_path).exists())
            and s.identity.is_complete()
            and bool(s.experiment_code)
        )

    def clear(self) -> None:
        self._state = SubmissionState()
        self.state_changed.emit()


# ---- 模块级单例（惰性创建，确保在 QApplication 之后构造 QObject）----
_singleton: "SubmissionStateManager | None" = None


def shared() -> SubmissionStateManager:
    """获取共享状态管理器单例。"""
    global _singleton
    if _singleton is None:
        _singleton = SubmissionStateManager()
    return _singleton
