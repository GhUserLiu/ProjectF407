#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
反馈/报告生成器
Feedback & Report Generators

两类输出：
1) 学生反馈（直击式）：置顶提交校验 → 成绩 → 必须修正的问题（逐条缺失/错误 +
   正确答案）→ 代码与编译问题 → 思考题核对 → 提升一级的具体动作。
   目的：让学生据此把作业"拔高一个层次"。
2) 教师分析报告：班级成绩统计、等级分布、各维度薄弱分析、排名、高频具体失分。

均以纯文本/Markdown 生成，便于写 .md 与 .docx。
"""

from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional


def _safe_rate(earned: float, mx: float) -> float:
    return (earned / mx) if mx > 0 else 0.0


# ============================================================
# 提交校验渲染（advisory，置顶）
# ============================================================
_SEV_LABEL = {'error': '错误', 'warning': '警告', 'info': '提示'}
_SEV_ORDER = {'error': 0, 'warning': 1, 'info': 2}


def _render_validation(v: Optional[Dict]) -> List[str]:
    """渲染提交校验结果。无问题返回空列表（不显示该块）。"""
    if not v:
        return []
    issues = v.get('issues') or []
    if not issues:
        return []
    lines = ["【提交校验】（格式/完整性问题，先于内容修正；不影响本次评分）"]
    for it in sorted(issues, key=lambda x: _SEV_ORDER.get(x.get('severity', 'info'), 3)):
        sev = _SEV_LABEL.get(it.get('severity', 'info'), '提示')
        lines.append(f"- [{sev}] {it.get('message', '')}")
        if it.get('fix'):
            lines.append(f"    修正：{it['fix']}")
    return lines


# ============================================================
# 学生反馈（直击式）
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
    """生成单个学生的直击式反馈：直指错误/不完美，给出正确答案与可提升动作。"""
    name = report.get("name", "同学")
    sid = report.get("student_id", "")
    total = report.get("total_score", 0)
    max_score = report.get("max_score", 100)
    bonus = report.get("bonus_total", 0) or 0
    grade = report.get("grade", "N/A")
    cat_scores = report.get("category_scores", []) or []
    issues = report.get("issues", []) or []
    thinking = report.get("thinking_check", []) or []
    validation = report.get("validation_report")

    overall_rate = _safe_rate(total, max_score)

    lines: List[str] = []
    lines.append(f"{name} 同学（学号 {sid}，{class_name}）：")
    lines.append("")
    lines.append(f"本次实验「{experiment_id}」批阅完成。下面直接指出失分点与不完美之处，"
                 "并给出正确答案和提升方向，请逐项对照修改。")
    lines.append("")

    # 0. 提交校验（置顶）
    val_block = _render_validation(validation)
    if val_block:
        lines.extend(val_block)
        lines.append("")

    # 1. 成绩
    lines.append("【成绩与定级】")
    lines.append(f"总分：{total}/{max_score}（{overall_rate*100:.1f}%），等级：{grade}")
    if bonus:
        lines.append(f"含基础分外加分：{bonus:.0f} 分（如组长加分）")
    lines.append("")

    # 简洁版
    if concise:
        must_fix = [i for i in issues if i.get('type') in ('criterion', 'build')
                    and i.get('points_lost', 0) > 0]
        for it in sorted(must_fix, key=lambda x: -x.get('points_lost', 0))[:2]:
            kw = f"（缺：{'、'.join(it.get('missing_keywords', []))}）" if it.get('missing_keywords') else ""
            lines.append(f"- 必改：[{it.get('category', '')}] {it.get('criterion', '')}{kw}"
                         f"，影响 {it.get('points_lost', 0)} 分")
            if it.get('expected'):
                lines.append(f"  正确应为：{it['expected']}")
        lines.append("")
        lines.append(_closing(overall_rate))
        return "\n".join(lines)

    # 2. 各部分得分
    if cat_scores:
        lines.append("【各部分得分】")
        for cs in cat_scores:
            cname = cs.get("category_name") or cs.get("category_id", "")
            e = float(cs.get("earned_points", 0) or 0)
            m = float(cs.get("max_points", 0) or 0)
            # 编译类"无法评估"（已跳过/无 Makefile/工具链缺失等）：不计入总分，
            # 单独标注，避免显示误导性的"0/15 ⚠失分较多"。
            details = cs.get("details") or []
            d0 = details[0] if isinstance(details, list) and details else {}
            br = d0.get("build_result") if isinstance(d0, dict) else None
            bstatus = (br.get("status") or "").lower() if isinstance(br, dict) else ""
            fb_txt = d0.get("feedback", "") if isinstance(d0, dict) else ""
            if bstatus in ("skipped", "not_found", "error", "timeout") or "已跳过" in fb_txt:
                lines.append(f"- {cname}：已跳过（未提取到可编译工程，不计入总分）")
                continue
            rate = _safe_rate(e, m)
            flag = "" if rate >= 0.6 else "  ⚠失分较多"
            lines.append(f"- {cname}：{e}/{m}（{rate*100:.0f}%）{flag}")
        lines.append("")

    # 3. 必须修正的问题（逐条：缺失关键词 + 正确答案 + 影响分值）
    must_fix = [i for i in issues if i.get('type') in ('criterion', 'build')]
    if must_fix:
        lines.append("【必须修正的问题】")
        for it in sorted(must_fix, key=lambda x: -x.get('points_lost', 0)):
            head = f"- [{it.get('category', '')}] {it.get('criterion', '')}"
            if it.get('missing_keywords'):
                head += f"：未体现「{'、'.join(it['missing_keywords'])}」"
            elif it.get('message'):
                head += f"：{it['message']}"
            head += f"（影响 {it.get('points_lost', 0)} 分）"
            lines.append(head)
            if it.get('expected'):
                lines.append(f"    ▶ 正确应为：{it['expected']}")
            if it.get('fix'):
                lines.append(f"    ▶ 怎么改：{it['fix']}")
        lines.append("")

    # 4. 代码与编译问题
    code_issues = [i for i in issues if i.get('type') == 'code']
    build_issue = next((i for i in issues if i.get('type') == 'build'
                        and i.get('severity') in ('error', 'warning')), None)
    if code_issues or build_issue:
        lines.append("【代码与编译问题】")
        if build_issue:
            lines.append(f"- 编译：{build_issue.get('message', '未通过')}"
                         + (f"（{build_issue.get('detail', '')}）" if build_issue.get('detail') else ""))
            if build_issue.get('fix'):
                lines.append(f"    ▶ {build_issue['fix']}")
        for it in code_issues:
            sev = (it.get('severity', 'info') or 'info').upper()
            loc = f"@行{it['line']}" if it.get('line') else ""
            lines.append(f"- [{sev}{loc}] {it.get('message', '')}")
            if it.get('fix'):
                lines.append(f"    ▶ 建议：{it['fix']}")
        lines.append("")

    # 5. 思考题核对
    if thinking:
        unanswered = [q for q in thinking if not q.get('answered')]
        lines.append("【思考题核对】")
        if unanswered:
            lines.append(f"未作答：{', '.join(q['id'] for q in unanswered)}（参考下方方向补答）")
        for q in thinking:
            mark = "✓" if q.get('answered') else "✗"
            lines.append(f"- {q.get('id')} {mark}")
            if q.get('expected'):
                lines.append(f"    参考方向：{q['expected']}")
        lines.append("")

    # 6. 提升一级的具体动作（quick-wins，按可回收分值排序）
    quickwins = [i for i in issues if i.get('type') == 'criterion' and i.get('points_lost', 0) > 0]
    if quickwins:
        total_recoverable = sum(i.get('points_lost', 0) for i in quickwins)
        lines.append("【提升一级的具体动作】（按可回收分值排序）")
        lines.append(f"理论上修正这些问题可回收约 {total_recoverable:.0f} 分：")
        for it in sorted(quickwins, key=lambda x: -x.get('points_lost', 0))[:6]:
            lines.append(f"- 补强「{it.get('criterion', '')}」→ 可回收 {it.get('points_lost', 0)} 分"
                         + (f"（对照：{it['expected']}）" if it.get('expected') else ""))
        lines.append("")

    # 收尾（简短、导向行动，不堆表扬）
    lines.append(_closing(overall_rate))
    return "\n".join(lines)


def _closing(overall_rate: float) -> str:
    """按总得分率给出一句简短、导向行动的收尾。"""
    if overall_rate >= 0.85:
        return "整体扎实。按上面少量待改进项打磨即可冲击更高等级。"
    if overall_rate >= 0.6:
        return "按「必须修正的问题」与「提升一级的具体动作」逐项落实，下次可显著提分。"
    return "待改进项较多，请优先完成「提交校验」与失分最大的几项，循序渐进。"


# ============================================================
# 教师分析报告（消费 class_analysis.ClassAnalysis，不重复计算）
# ============================================================
def build_teacher_report(
    class_name: str,
    experiment_id: str,
    reports: List[Dict],
) -> str:
    """生成班级教师分析报告。统计/分布/维度/排名来自 class_analysis.analyze()；
    另从个人报告的 issues 聚合「高频具体失分」。"""
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
                f"（{r['rate'] * 100:.0f}%）"
            )
        weakest = a.category_analysis[0]
        lines.append("")
        lines.append(f"**全班最薄弱维度**：「{weakest['name']}」（{weakest['rate'] * 100:.0f}%），建议在后续教学中重点强化。")
        lines.append("")

    # 高频具体失分（从 issues 聚合，比含糊的"维度薄弱"更可操作）
    freq = _aggregate_issues(a.reports)
    if freq:
        lines.append("## 四、高频具体失分（按出现人数）")
        for msg, c in freq:
            lines.append(f"- {msg}（{c} 人）")
        lines.append("")

    lines.append("## 五、成绩排名")
    lines.append("| 排名 | 学号 | 姓名 | 总分 | 等级 |")
    lines.append("|---|---|---|---|---|")
    for i, r in enumerate(a.ranking, 1):
        lines.append(f"| {i} | {r.get('student_id', '')} | {r.get('name', '')} | "
                     f"{float(r.get('total_score', 0)):.1f} | {r.get('grade', '')} |")
    lines.append("")

    lines.append("## 六、共性薄弱点与亮点")
    if a.common_weaknesses:
        lines.append("**高频薄弱点：**")
        lines.extend(f"- {t}" for t in a.common_weaknesses)
    else:
        lines.append("**高频薄弱点：** （无聚合数据，详见各维度得分率）")
    if a.common_strengths:
        lines.append("**高频亮点：**")
        lines.extend(f"- {t}" for t in a.common_strengths)
    lines.append("")

    lines.append("## 七、教学建议")
    for r in a.category_analysis[:2]:
        if r["rate"] < 0.7:
            lines.append(f"- 「{r['name']}」全班平均仅 {r['rate'] * 100:.0f}%，建议增加相关讲解与练习。")
    if a.pass_rate < 60:
        lines.append(f"- 及格率仅 {a.pass_rate:.0f}%，整体偏弱，建议组织专项辅导。")
    if a.std > 20:
        lines.append(f"- 成绩标准差 {a.std:.0f}，两极分化明显，建议分层辅导。")
    lines.append("")
    return "\n".join(lines)


def _aggregate_issues(reports: List[Dict], top_n: int = 8) -> List[tuple]:
    """从个人报告 issues 聚合高频具体失分条目。返回 [(描述, 人数), ...]。"""
    counter: Counter = Counter()
    for r in reports:
        seen = set()
        for it in (r.get("issues") or []):
            if it.get("type") not in ("criterion", "build"):
                continue
            key = f"[{it.get('category', '')}] {it.get('criterion', '')}"
            if key not in seen:
                seen.add(key)
                counter[key] += 1
    return counter.most_common(top_n)
