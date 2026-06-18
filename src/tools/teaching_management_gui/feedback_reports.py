#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
反馈/报告生成器
Feedback & Report Generators

两类输出：
1) 学生反馈（丰富文本）：解释评分依据、各部分得失、错误点与可提升方向；
2) 教师分析报告：班级成绩统计、等级分布、各维度薄弱分析、排名、共性问题。

均以纯文本/Markdown 生成，便于写 .md 与 .docx。
"""

from datetime import datetime
from typing import Dict, List, Optional


# ---------------- 评分维度点评（按得分率）----------------
def _rate_comment(rate: float) -> str:
    """按得分率给出一句点评。"""
    if rate >= 0.9:
        return "掌握扎实，表现优秀"
    if rate >= 0.75:
        return "较好掌握，仍有提升空间"
    if rate >= 0.6:
        return "基本掌握，建议巩固"
    return "较薄弱，需重点加强"


def _safe_rate(earned: float, mx: float) -> float:
    return (earned / mx) if mx > 0 else 0.0


# ============================================================
# 学生反馈（丰富文本）
# ============================================================
def build_student_feedback(
    report: Dict,
    class_name: str = "",
    experiment_id: str = "",
    include_strengths: bool = True,
    include_weaknesses: bool = True,
    include_suggestions: bool = True,
    concise: bool = False,
) -> str:
    """生成单个学生的丰富文本反馈。

    在原"优点/不足/建议"基础上，加入各评分维度的自动点评，解释评分依据。
    """
    name = report.get("name", "同学")
    sid = report.get("student_id", "")
    total = report.get("total_score", 0)
    max_score = report.get("max_score", 100)
    grade = report.get("grade", "N/A")
    cat_scores = report.get("category_scores", []) or []

    overall_rate = _safe_rate(total, max_score)
    lines: List[str] = []
    lines.append(f"{name} 同学（学号 {sid}，{class_name}）：")
    lines.append("")
    lines.append(f"本次实验「{experiment_id}」批阅已完成。下面帮助你了解本次评分依据与提升方向。")
    lines.append("")
    lines.append("【成绩概览】")
    lines.append(f"总分：{total}/{max_score}（{overall_rate*100:.1f}%），等级：{grade}")
    lines.append("")

    # 找出薄弱维度（得分率 < 0.6），供简版与详细版共用
    weak_cats = []
    for cs in cat_scores:
        e = float(cs.get("earned_points", 0) or 0)
        m = float(cs.get("max_points", 0) or 0)
        if m > 0 and _safe_rate(e, m) < 0.6:
            weak_cats.append(cs.get("category_name") or cs.get("category_id", ""))

    strengths = report.get("strengths", []) or []
    weaknesses = report.get("weaknesses", []) or []
    suggestions = report.get("suggestions", []) or []

    # 简洁版：只给成绩 + 1 个最关键失分点 + 1 条建议，省略逐条维度点评
    if concise:
        if include_weaknesses:
            if weaknesses:
                lines.append(f"【失分点】{weaknesses[0]}")
            elif weak_cats:
                lines.append(f"【失分点】在「{'、'.join(weak_cats)}」失分较多，请重点回顾。")
            lines.append("")
        if include_suggestions:
            if suggestions:
                lines.append(f"【提升建议】{suggestions[0]}")
            elif weak_cats:
                lines.append(f"【提升建议】针对「{'、'.join(weak_cats)}」加强练习。")
            lines.append("")
        lines.append(_closing(overall_rate))
        return "\n".join(lines)

    # 详细版：各部分得分 + 自动点评（解释评分依据）
    if cat_scores:
        lines.append("【各部分得分与点评】")
        for cs in cat_scores:
            cname = cs.get("category_name") or cs.get("category_id", "")
            e = float(cs.get("earned_points", 0) or 0)
            m = float(cs.get("max_points", 0) or 0)
            rate = _safe_rate(e, m)
            comment = _rate_comment(rate)
            lines.append(f"- {cname}：{e}/{m}（{rate*100:.0f}%）— {comment}")
        lines.append("")

    # 优点
    if include_strengths and strengths:
        lines.append("【你的亮点】")
        lines.extend(f"- {s}" for s in strengths)
        lines.append("")

    # 失分点 / 错误点
    if include_weaknesses and (weaknesses or weak_cats):
        lines.append("【失分点 / 需注意】")
        for w in weaknesses:
            lines.append(f"- {w}")
        if weak_cats and not weaknesses:
            lines.append(f"- 在「{('、'.join(weak_cats))}」维度失分较多，请重点回顾相关内容。")
        elif weak_cats:
            lines.append(f"- 综合来看，「{'、'.join(weak_cats)}」是你相对薄弱的环节。")
        lines.append("")

    # 改进建议
    if include_suggestions and suggestions:
        lines.append("【可提升方向】")
        lines.extend(f"- {s}" for s in suggestions)
        lines.append("")
    elif include_suggestions and weak_cats:
        lines.append("【可提升方向】")
        lines.append(f"- 针对「{'、'.join(weak_cats)}」，建议结合课堂内容与示例代码加强练习。")
        lines.append("")

    # 结尾
    lines.append(_closing(overall_rate))
    return "\n".join(lines)


def _closing(overall_rate: float) -> str:
    """按总得分率给出分档鼓励语。"""
    if overall_rate >= 0.85:
        return "表现很出色，继续保持！"
    if overall_rate >= 0.6:
        return "整体不错，针对上面的薄弱点再下点功夫会更好。"
    return "本次有较多需要改进的地方，按上述方向逐项突破，下次一定能进步。"


# ============================================================
# 教师分析报告（消费 class_analysis.ClassAnalysis，不重复计算）
# ============================================================
def build_teacher_report(
    class_name: str,
    experiment_id: str,
    reports: List[Dict],
) -> str:
    """生成班级教师分析报告。

    统计/分布/维度/排名/共性问题均来自 class_analysis.analyze()，
    与「班级报告」对话框共用同一套计算，避免重复。
    """
    from tools.teaching_management_gui.class_analysis import analyze
    a = analyze(reports, class_name, experiment_id)

    lines: List[str] = []
    lines.append(f"# 教学分析报告 — {class_name}")
    lines.append(f"实验：{experiment_id}　|　生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    if a.n == 0:
        lines.append("（无可用批阅数据）")
        return "\n".join(lines)

    lines.append("## 一、成绩统计")
    lines.append(f"- 参评学生：{a.n}")
    lines.append(f"- 平均分：{a.avg:.1f}")
    lines.append(f"- 中位数：{a.median:.1f}")
    lines.append(f"- 最高 / 最低：{a.max_score:.1f} / {a.min_score:.1f}")
    lines.append(f"- 标准差：{a.std:.1f}")
    lines.append(f"- 及格率（≥60%）：{a.pass_rate:.1f}%")
    lines.append("")

    lines.append("## 二、等级分布")
    for g in sorted(a.grade_distribution.keys()):
        c = a.grade_distribution[g]
        bar = "█" * round(c / a.n * 20)
        lines.append(f"- {g}：{c} 人（{c / a.n * 100:.1f}%） {bar}")
    lines.append("")

    if a.category_analysis:
        lines.append("## 三、各评分维度分析（按平均得分率升序，薄弱在前）")
        for r in a.category_analysis:
            lines.append(
                f"- {r['name']}：{r['avg_earned']:.1f}/{r['avg_max']:.1f}"
                f"（{r['rate'] * 100:.0f}%）— {_rate_comment(r['rate'])}"
            )
        weakest = a.category_analysis[0]
        lines.append("")
        lines.append(f"**全班最薄弱维度**：「{weakest['name']}」（{weakest['rate'] * 100:.0f}%），建议在后续教学中重点强化。")
        lines.append("")

    lines.append("## 四、成绩排名")
    lines.append("| 排名 | 学号 | 姓名 | 总分 | 等级 |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(a.ranking, 1):
        lines.append(f"| {i} | {r.get('student_id', '')} | {r.get('name', '')} | "
                     f"{float(r.get('total_score', 0)):.1f} | {r.get('grade', '')} |")
    lines.append("")

    lines.append("## 五、共性薄弱点与亮点")
    if a.common_weaknesses:
        lines.append("**高频薄弱点：**")
        lines.extend(f"- {t}" for t in a.common_weaknesses)
    else:
        lines.append("**高频薄弱点：** （无聚合数据，详见各维度得分率）")
    if a.common_strengths:
        lines.append("**高频亮点：**")
        lines.extend(f"- {t}" for t in a.common_strengths)
    lines.append("")

    lines.append("## 六、教学建议")
    for r in a.category_analysis[:2]:
        if r["rate"] < 0.7:
            lines.append(f"- 「{r['name']}」全班平均仅 {r['rate'] * 100:.0f}%，建议增加相关讲解与练习。")
    if a.pass_rate < 60:
        lines.append(f"- 及格率仅 {a.pass_rate:.0f}%，整体偏弱，建议组织专项辅导。")
    if a.std > 20:
        lines.append(f"- 成绩标准差 {a.std:.0f}，两极分化明显，建议分层辅导。")
    lines.append("")
    return "\n".join(lines)
