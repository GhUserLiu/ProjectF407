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


def _make_result(sid, name, source_dir_name, score, bonus=0.0, issues=None,
                 group_key="", group_members=None):
    """构造一个 GradingResult，compilation_result.project_path 指向给定源码目录名。

    source_dir_name=None 表示无源码（compilation_result 置空，模拟 not_submitted）。
    group_key/group_members 用于测试组级 group_submitter_count 盖章。
    """
    r = GradingResult(
        student_id=sid,
        name=name,
        class_name="汽服2301B班",
        total_score=score,
        max_score=100.0,
        bonus_total=bonus,
        grade="N/A",
        group_key=group_key,
        group_members=list(group_members or []),
        issues=list(issues or []),
    )
    # project_path.name 即源码目录名（模拟 organizer 产出的 ...-源代码 目录）
    if source_dir_name is not None:
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


class TestSubmitterCount:
    """group_submitter_count：本组「各自提交源码」的去重人数（≥2 触发重复提交提醒）。"""

    GK = "23071140125"
    MEMBERS = [("23071140125", "靳皓杰"), ("23071140135", "薛松涛"), ("23071140136", "李志飞")]

    def test_count_three_when_all_members_self_submit(self):
        """3 人各自提交（每人源码目录含本人学号）→ count=3，全组同值。"""
        out = dedupe_team_members([
            _make_result("23071140125", "靳皓杰", "汽服2301B班-23071140125-靳皓杰-源代码", 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140135", "薛松涛", "汽服2301B班-23071140135-薛松涛-源代码", 65.0,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140136", "李志飞", "汽服2301B班-23071140136-李志飞-源代码", 76.9,
                         group_key=self.GK, group_members=self.MEMBERS),
        ])
        assert {r.group_submitter_count for r in out} == {3}

    def test_count_one_when_only_leader_submits(self):
        """仅组长提交，组员回退到组长源码（学号不命中）→ count=1。"""
        leader_src = "汽服2301B班-23071140125-靳皓杰-源代码"
        out = dedupe_team_members([
            _make_result("23071140125", "靳皓杰", leader_src, 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140135", "薛松涛", leader_src, 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140136", "李志飞", leader_src, 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
        ])
        assert {r.group_submitter_count for r in out} == {1}

    def test_count_two_when_two_of_three_submit(self):
        """组长 + 一名组员各自提交，另一组员回退到组长源码 → count=2。"""
        out = dedupe_team_members([
            _make_result("23071140125", "靳皓杰", "汽服2301B班-23071140125-靳皓杰-源代码", 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140135", "薛松涛", "汽服2301B班-23071140135-薛松涛-源代码", 65.0,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140136", "李志飞", "汽服2301B班-23071140125-靳皓杰-源代码", 81.9,
                         group_key=self.GK, group_members=self.MEMBERS),
        ])
        assert {r.group_submitter_count for r in out} == {2}

    def test_count_zero_when_no_source(self):
        """全组均无源码 → count=0（不误触发提醒）。"""
        out = dedupe_team_members([
            _make_result("23071140125", "靳皓杰", None, 50.0,
                         group_key=self.GK, group_members=self.MEMBERS),
            _make_result("23071140135", "薛松涛", None, 50.0,
                         group_key=self.GK, group_members=self.MEMBERS),
        ])
        assert {r.group_submitter_count for r in out} == {0}

    def test_count_not_set_for_individual_experiment(self):
        """个人实验（无 group_key）→ 不盖章，保持默认 0。"""
        r = _make_result("23071140141", "李全", "汽服2301B班-23071140141-李全-源代码", 50.0)
        out = dedupe_team_members([r])
        assert out[0].group_submitter_count == 0
