# -*- coding: utf-8 -*-
"""
dedupe_team_members 单元测试

覆盖：
- 自评归因优先（学号命中源码目录名）——不被队友源码覆盖
- 无自评时回退最高分（共享组长源码）
- 同组勿重复提交提醒（关联>1个不同源码目录才触发）
- 个人实验（无重复）为空操作
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, "src")

from tools.auto_grading.grading_engine import (
    dedupe_team_members,
    GradingResult,
)
from tools.auto_grading.build_checker import BuildResult, BuildStatus


def _make_result(sid, name, source_dir_name, score, bonus=0.0, issues=None):
    """构造一个 GradingResult，compilation_result.project_path 指向给定源码目录名。"""
    r = GradingResult(
        student_id=sid,
        name=name,
        class_name="汽服2301B班",
        total_score=score,
        max_score=100.0,
        bonus_total=bonus,
        grade="N/A",
        issues=list(issues or []),
    )
    # project_path.name 即源码目录名（模拟 organizer 产出的 ...-源代码 目录）
    r.compilation_result = BuildResult(
        status=BuildStatus.SKIPPED,
        project_name=f"{sid}-{name}",
        project_path=Path(source_dir_name),
        success=False,
    )
    return r


class TestSelfSourcedPreference:
    def test_prefers_self_over_higher_scoring_teammate(self):
        """138 自评(keil,低分) vs 134 报告里的 138(嵌套,高分) → 保留自评。"""
        self_src = "汽服2301B班-23071140138-范才兴-源代码"
        mate_src = "汽服2301B班-23071140134-聂智聪-源代码"
        # 自评低分、队友源码(在134报告里)高分
        r_self = _make_result("23071140138", "范才兴", self_src, score=40.0)
        r_mate = _make_result("23071140138", "范才兴", mate_src, score=80.0)
        out = dedupe_team_members([r_self, r_mate])
        assert len(out) == 1
        # 即使队友那条分数更高，也保留自评
        assert out[0].total_score == 40.0
        assert Path(out[0].compilation_result.project_path).name == self_src

    def test_falls_back_to_max_when_no_self(self):
        """该生仅作为组员出现(无自评) → 取最高分。"""
        a = _make_result("23071140140", "张磊", "汽服2301B班-23071140134-聂智聪-源代码", 60.0)
        b = _make_result("23071140140", "张磊", "汽服2301B班-23071140138-范才兴-源代码", 80.0)
        out = dedupe_team_members([a, b])
        assert len(out) == 1
        assert out[0].total_score == 80.0

    def test_single_result_passthrough(self):
        r = _make_result("23071140141", "李全", "汽服2301B班-23071140141-李全-源代码", 50.0)
        out = dedupe_team_members([r])
        assert out == [r]


class TestDuplicateSubmissionReminder:
    def test_reminder_added_when_multiple_distinct_sources(self):
        """关联>1个不同源码目录 → 追加「同组勿重复提交」提醒。"""
        self_src = "汽服2301B班-23071140138-范才兴-源代码"
        r_self = _make_result("23071140138", "范才兴", self_src, 40.0)
        r_mate = _make_result("23071140138", "范才兴", "汽服2301B班-23071140134-聂智聪-源代码", 80.0)
        out = dedupe_team_members([r_self, r_mate])
        reminders = [i for i in out[0].issues if i.get("criterion") == "同组勿重复提交"]
        assert len(reminders) == 1
        assert reminders[0]["severity"] == "info"
        assert reminders[0]["points_lost"] == 0

    def test_no_reminder_when_same_source_only(self):
        """多份结果但同一源码目录(同一份被多次上传) → 不提醒。"""
        src = "汽服2301B班-23071140134-聂智聪-源代码"
        # 同一源码目录、不同分数（模拟同一份报告被多次处理）
        r1 = _make_result("23071140134", "聂智聪", src, 70.0)
        r2 = _make_result("23071140134", "聂智聪", src, 75.0)
        out = dedupe_team_members([r1, r2])
        reminders = [i for i in out[0].issues if i.get("criterion") == "同组勿重复提交"]
        assert reminders == []

    def test_no_reminder_for_single_result(self):
        r = _make_result("23071140141", "李全", "汽服2301B班-23071140141-李全-源代码", 50.0)
        out = dedupe_team_members([r])
        assert out[0].issues == []


class TestOrderPreservation:
    def test_output_preserves_first_appearance_order(self):
        r_b = _make_result("23071140140", "张磊", "汽服2301B班-23071140140-张磊-源代码", 50.0)
        r_a = _make_result("23071140138", "范才兴", "汽服2301B班-23071140138-范才兴-源代码", 60.0)
        out = dedupe_team_members([r_b, r_a])
        # 按首次出现顺序：张磊 在前
        assert out[0].student_id == "23071140140"
        assert out[1].student_id == "23071140138"
