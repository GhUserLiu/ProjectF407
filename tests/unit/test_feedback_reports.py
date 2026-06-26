# -*- coding: utf-8 -*-
"""
feedback_reports 单元测试 —— 聚焦「同组多人重复提交」提醒：

- _distinct_submitters：新字段优先 + project_name 兜底
- build_group_feedback：≥2 人各自提交时置顶提醒，并修正"共用同一份报告"的虚假措辞；
  单提交者保持原有"共用同一份"行为（回归保护）。
"""

import sys

sys.path.insert(0, "src")

from tools.teaching_management_gui.feedback_reports import (  # noqa: E402
    build_group_feedback,
    _distinct_submitters,
)


MEMBERS = [("23071140125", "靳皓杰"), ("23071140135", "薛松涛"), ("23071140136", "李志飞")]


def _report(sid, name, *, total=80.0, leader=False, gk="23071140125",
            comp_earned=0.0, project_name=None, submitter_count=None,
            members=None):
    """构造一份最小可渲染的个人报告 dict。

    project_name 模拟 compilation 类目 build_result.project_name（自我归因后指向本人源码），
    供 _distinct_submitters 兜底；submitter_count 模拟批阅时盖章的新字段。
    代码类分项默认全一致 → _members_share_source 返回 True（用于复现靳组 shared=True 的场景）。
    """
    comp_details = ([{"build_result": {"project_name": project_name, "status": "failed"}}]
                    if project_name is not None else [])
    cat = [
        {"category_id": "compilation", "category_name": "编译检查", "max_points": 10,
         "earned_points": comp_earned, "details": comp_details},
        {"category_id": "non_blocking", "category_name": "非阻塞", "max_points": 10,
         "earned_points": 10.0, "details": []},
        {"category_id": "code_quality", "category_name": "代码质量", "max_points": 15,
         "earned_points": 14.7, "details": []},
        {"category_id": "functionality", "category_name": "功能实现", "max_points": 10,
         "earned_points": 6.6, "details": []},
    ]
    r = {
        "student_id": sid, "name": name, "class_name": "汽服2301B班",
        "total_score": total, "max_score": 100.0, "grade": "C",
        "bonus_total": 5.0 if leader else 0.0, "is_team_leader": leader,
        "group_key": gk, "group_members": members or [],
        "category_scores": cat, "issues": [], "thinking_check": [],
        "validation_report": None,
    }
    if submitter_count is not None:
        r["group_submitter_count"] = submitter_count
    return r


class TestDistinctSubmitters:
    def test_uses_new_field_when_present(self):
        reps = [_report("23071140125", "靳皓杰", submitter_count=3, members=MEMBERS)]
        assert _distinct_submitters(reps) == 3

    def test_field_overrides_project_name(self):
        """有新字段时优先用字段，忽略 project_name 兜底。"""
        reps = [_report("23071140125", "靳皓杰", submitter_count=1,
                        project_name="23071140125-靳皓杰", members=MEMBERS)]
        assert _distinct_submitters(reps) == 1

    def test_fallback_project_name_counts_distinct_owners(self):
        reps = [
            _report("23071140125", "靳皓杰", project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140135", "薛松涛", project_name="23071140135-薛松涛", members=MEMBERS),
            _report("23071140136", "李志飞", project_name="23071140136-李志飞", members=MEMBERS),
        ]
        assert _distinct_submitters(reps) == 3

    def test_fallback_dedupes_same_owner(self):
        """多人均回退到组长源码（同 project_name）→ 计为 1。"""
        reps = [
            _report("23071140125", "靳皓杰", project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140135", "薛松涛", project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140136", "李志飞", project_name="23071140125-靳皓杰", members=MEMBERS),
        ]
        assert _distinct_submitters(reps) == 1

    def test_fallback_single_member(self):
        reps = [_report("23071140121", "成安旭", project_name="23071140121-成安旭")]
        assert _distinct_submitters(reps) == 1

    def test_fallback_no_compilation_returns_zero(self):
        reps = [
            _report("23071140125", "靳皓杰", project_name=None, members=MEMBERS),
            _report("23071140135", "薛松涛", project_name=None, members=MEMBERS),
        ]
        assert _distinct_submitters(reps) == 0


class TestGroupFeedbackNotice:
    def test_multi_submit_shows_notice_and_drops_false_claim(self):
        """3 人各自提交（3 个不同 project_name）→ 出现提醒，且不再声称共用同一份报告。"""
        reps = [
            _report("23071140125", "靳皓杰", leader=True, total=81.9,
                    project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140135", "薛松涛", total=65.0,
                    project_name="23071140135-薛松涛", members=MEMBERS),
            _report("23071140136", "李志飞", total=76.9,
                    project_name="23071140136-李志飞", members=MEMBERS),
        ]
        text = build_group_feedback(reps, "汽服2301B班", "final-project")
        assert "本组有 3 名成员各自上传" in text
        assert "提交提醒" in text
        assert "只需由组长一人提交一份" in text
        assert "共用同一份工程与报告" not in text

    def test_multi_submit_overrides_shared_true(self):
        """代码类分项全一致（shared=True）但 3 人各自提交 → 仍触发提醒（靳组真实场景）。"""
        reps = [
            _report("23071140125", "靳皓杰", leader=True,
                    project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140135", "薛松涛",
                    project_name="23071140135-薛松涛", members=MEMBERS),
            _report("23071140136", "李志飞",
                    project_name="23071140136-李志飞", members=MEMBERS),
        ]
        text = build_group_feedback(reps, "汽服2301B班", "final-project")
        assert "本组有 3 名成员各自上传" in text
        assert "共用同一份工程与报告" not in text

    def test_explicit_field_drives_notice(self):
        """新字段 group_submitter_count=2 → 触发（即便无 project_name 兜底数据）。"""
        reps = [
            _report("23071140125", "靳皓杰", leader=True, submitter_count=2, members=MEMBERS),
            _report("23071140135", "薛松涛", submitter_count=2, members=MEMBERS),
        ]
        text = build_group_feedback(reps, "汽服2301B班", "final-project")
        assert "本组有 2 名成员各自上传" in text
        assert "共用同一份工程与报告" not in text

    def test_single_submitter_keeps_shared_claim(self):
        """仅组长提交（他人 project_name 均回退到组长）→ 不触发、保留'共用同一份'（回归保护）。"""
        reps = [
            _report("23071140125", "靳皓杰", leader=True,
                    project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140135", "薛松涛",
                    project_name="23071140125-靳皓杰", members=MEMBERS),
            _report("23071140136", "李志飞",
                    project_name="23071140125-靳皓杰", members=MEMBERS),
        ]
        text = build_group_feedback(reps, "汽服2301B班", "final-project")
        assert "各自上传" not in text
        assert "提交提醒" not in text
        assert "共用同一份工程与报告" in text
