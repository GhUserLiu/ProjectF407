#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
整合评分引擎
Auto Grading Engine

以 rubric.json 为唯一事实来源，按每个 category 的 grading_method 派发：
- build         → BuildChecker（真实编译）
- code_analysis → EnhancedCodeAnalyzer（真实源码静态分析）
- keyword       → RubricGrader 逐准则关键词匹配
- manual        → 读 rubric default_points
- conditional   → 组长加分（基础分外）

每个 category 产出一个 CategoryScore；base 总分封顶 rubric.total_points(100)，
bonus（points_outside_base）单列；等级按 base/100 计算。

同时产出：
- validation_report：提交完整性校验（advisory，不改分）
- issues：结构化失分项（供直击式学生反馈）
- thinking_check：思考题 Q1~Q7 作答核对
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

from .config import AutoGradingConfig
from .build_checker import BuildChecker, BuildResult, BuildStatus
from .submission_processor import ProcessedSubmission
from .submission_validator import SubmissionValidator, ValidationReport


@dataclass
class CategoryScore:
    """评分类别得分"""
    category_id: str           # 类别ID
    category_name: str         # 类别名称
    max_points: float          # 满分
    earned_points: float       # 得分
    details: List[Dict] = field(default_factory=list)  # 得分详情


@dataclass
class GradingResult:
    """评分结果"""
    student_id: str            # 学号
    name: str                  # 姓名
    class_name: str            # 班级

    # 评分
    total_score: float = 0.0   # 基础总分（封顶 max_score）
    max_score: float = 100.0   # 满分（rubric.total_points）
    bonus_total: float = 0.0   # 基础分外加分（如组长加分）
    is_team_leader: bool = False  # 报告是否声明作者为组长（驱动组长加分）
    grade: str = "N/A"         # 等级（A/B/C/D/F）

    # 各类别得分（每类一个，与 rubric 对齐）
    category_scores: List[CategoryScore] = field(default_factory=list)

    # 详细信息
    compilation_result: Optional[BuildResult] = None
    code_analysis: Optional[Dict] = None
    report_analysis: Optional[Dict] = None

    # 校验与反馈
    validation_report: Optional[ValidationReport] = None
    issues: List[Dict] = field(default_factory=list)        # 结构化失分项
    thinking_check: List[Dict] = field(default_factory=list)  # 思考题核对

    # 旧字段（兼容/汇总）
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # 时间戳
    graded_at: datetime = field(default_factory=datetime.now)


# 自称为组长的句式（命中即判定作者为组长）
_LEADER_SELF_PATTERNS = [
    re.compile(r'担任组长'),
    re.compile(r'作为组长'),
    re.compile(r'我任组长'),
    re.compile(r'任组长'),
    re.compile(r'本人[^。\n]{0,6}组长'),
    re.compile(r'我[^。\n]{0,4}组长'),
    re.compile(r'我\s*[（(]\s*组长'),
    re.compile(r'组长[：:]\s*本人'),
    re.compile(r'组长[：:]\s*我(?!们)'),
]


def detect_team_leader(report_text: str, student_name: str) -> bool:
    """从实验报告文本判断作者是否声明自己为组长。

    - 报告含"本人/我担任组长""作为组长"等自称 → True
    - "组长：姓名" / "姓名（组长）" 中的姓名 == 学生姓名 → True
    - 只声明他人为组长，或完全未声明 → False（该组视为无组长，不加分）
    """
    if not report_text:
        return False
    for pat in _LEADER_SELF_PATTERNS:
        if pat.search(report_text):
            return True
    if student_name:
        # 组长：张三 / 组长为张三 / 组长:张三
        for m in re.finditer(r'组长[：:为是]\s*([^\s,，。、；;（(《<]{1,20})', report_text):
            tok = m.group(1)
            if student_name in tok or tok in student_name:
                return True
        # 张三（组长）
        for m in re.finditer(r'([一-龥A-Za-z·]{2,20})\s*[（(]\s*组长\s*[）)]', report_text):
            if m.group(1) == student_name:
                return True
    return False


class AutoGradingEngine:
    """自动评分引擎（rubric 驱动）"""

    def __init__(
        self,
        config: Optional[AutoGradingConfig] = None,
        rubric_path: Optional[Path] = None
    ):
        self.config = config or AutoGradingConfig()
        self.rubric_path = rubric_path

        # 初始化子模块
        self.build_checker = BuildChecker(self.config)
        self.validator = SubmissionValidator()

        # 延迟导入（避免循环依赖）
        try:
            from ..plagiarism.code_analysis.code_analyzer import EnhancedCodeAnalyzer
            from ..plagiarism.grading.grading import RubricGrader

            self.code_analyzer = EnhancedCodeAnalyzer
            self.rubric_grader = RubricGrader
        except ImportError as e:
            print(f"警告: 无法导入评分模块: {e}")
            self.code_analyzer = None
            self.rubric_grader = None

        # 加载并自检评分标准
        self.rubric = None
        if rubric_path and rubric_path.exists():
            self.rubric = self._load_rubric(rubric_path)

    # --------------------------------------------------------------
    # rubric 加载与自检
    # --------------------------------------------------------------
    def _load_rubric(self, rubric_path: Path) -> Dict:
        import json
        with open(rubric_path, 'r', encoding='utf-8') as f:
            rubric = json.load(f)
        self._validate_rubric(rubric)
        return rubric

    def _validate_rubric(self, rubric: Dict):
        """加载期 rubric 自检：base 分值和 == total_points；id 唯一；keyword 准则有关键词。"""
        cats = rubric.get('categories', [])
        ids = [c.get('id') for c in cats]
        dup = [i for i in set(ids) if ids.count(i) > 1]
        if dup:
            raise ValueError(f"rubric 类别 id 重复: {dup}")

        total_points = rubric.get('total_points', 100)
        base_sum = sum(c.get('points', 0) for c in cats if not c.get('points_outside_base'))
        if abs(base_sum - total_points) > 0.01:
            raise ValueError(
                f"rubric 基础分值和({base_sum}) != total_points({total_points})；"
                f"请检查 data/rubrics/rubric.json"
            )

        for c in cats:
            if c.get('grading_method', 'keyword') == 'keyword':
                for crit in c.get('criteria', []):
                    if not crit.get('keywords'):
                        print(f"警告: 准则 '{crit.get('description')}' 未配置 keywords")

    # --------------------------------------------------------------
    # 主评分入口
    # --------------------------------------------------------------
    def grade_submission(self, submission: ProcessedSubmission) -> GradingResult:
        result = GradingResult(
            student_id=submission.student_id,
            name=submission.name,
            class_name=submission.class_name
        )

        # 1. 提交完整性校验（advisory，不参与计分）
        try:
            result.validation_report = self.validator.validate(submission, self.rubric)
        except Exception as e:
            print(f"警告: 提交校验异常: {e}")
            result.validation_report = None

        # 无 rubric 时降级（不应发生，facade 已强制接通）
        if not self.rubric:
            result.max_score = 100.0
            result.grade = self._calculate_grade_default(result.total_score, result.max_score)
            return result

        # 2. RubricGrader 跑一次 keyword/manual 类别（需要报告文本）
        rg_result = None
        if self.rubric_grader and submission.report_text:
            try:
                grader = self.rubric_grader(self.rubric)
                rg_result = grader.grade(
                    submission.student_id,
                    submission.name,
                    submission.report_text,
                )
                result.report_analysis = {
                    'category_scores': {
                        cid: self._rg_category_to_dict(cs)
                        for cid, cs in rg_result.category_scores.items()
                    }
                }
            except Exception as e:
                print(f"警告: RubricGrader 执行失败: {e}")
                rg_result = None

        # 组长判定：从报告"团队信息与分工"等处提取；未声明则视为无组长
        is_leader = detect_team_leader(submission.report_text or "", submission.name or "")
        result.is_team_leader = is_leader

        # 3. 按 grading_method 派发，逐类产出 CategoryScore
        category_scores: List[CategoryScore] = []
        base_earned = 0.0
        bonus_total = 0.0
        excluded_points = 0.0   # 工具链缺失等「非学生责任」被排除的基数分（如编译 15 分）

        for cat in self.rubric.get('categories', []):
            method = cat.get('grading_method', 'keyword')

            cs = None
            if method == 'build':
                cs = self._grade_compilation(submission, cat)
            elif method == 'code_analysis':
                cs = self._grade_code_quality(submission, cat)
            elif method == 'source_check':
                cs = self._grade_source_check(submission, cat)
            elif method == 'conditional':
                cs = self._grade_conditional(cat, is_leader)
            else:  # keyword / manual
                cs = self._category_from_rubric_grader(rg_result, cat, submission)

            if cs is None:
                cs = CategoryScore(
                    category_id=cat['id'],
                    category_name=cat.get('name', cat['id']),
                    max_points=cat.get('points', 0),
                    earned_points=0.0,
                    details=[{'feedback': '无法评分（缺少必要材料）'}]
                )

            # 记录编译/代码分析详情，供反馈与兼容字段使用
            if method == 'build' and cs.details:
                br = cs.details[0].get('build_result')
                result.compilation_result = br
                # 工具链缺失（SKIPPED）：非学生责任，汇总时把该类分值排除出总分与等级基数，
                # 避免无工具链持续拖低预测分。仅对基础分内类别生效（bonus 类本就单列）。
                if (br is not None and getattr(br, 'status', None) == BuildStatus.SKIPPED
                        and not cat.get('points_outside_base')):
                    excluded_points += cat.get('points', 0)
            if method == 'code_analysis' and cs.details:
                result.code_analysis = cs.details[0].get('analysis')

            category_scores.append(cs)
            if cat.get('points_outside_base'):
                bonus_total += cs.earned_points
            else:
                base_earned += cs.earned_points

        result.category_scores = category_scores

        # 4. 汇总：base 封顶 total_points，bonus 单列
        total_points = self.rubric.get('total_points', 100)
        if excluded_points > 0:
            # 存在被排除的编译类（工具链缺失）：按「可评类别」折算总分与等级。
            # max_score 收缩为可评基数（如 100-15=85），等级按 base_earned/可评基数 折算回
            # /total_points 再套 grading_scale，保证学生不被工具链缺失系统性压低等级。
            assessable_max = max(total_points - excluded_points, 0.01)
            result.max_score = round(assessable_max, 1)
            result.total_score = round(min(base_earned, assessable_max), 1)
            effective = (base_earned / assessable_max) * total_points
            if 'grading_scale' in self.rubric:
                result.grade = self._calculate_grade(effective, self.rubric['grading_scale'])
            else:
                result.grade = self._calculate_grade_default(result.total_score, result.max_score)
        else:
            result.total_score = round(min(base_earned, total_points), 1)
            result.max_score = total_points
            if 'grading_scale' in self.rubric:
                result.grade = self._calculate_grade(result.total_score, self.rubric['grading_scale'])
            else:
                result.grade = self._calculate_grade_default(result.total_score, result.max_score)
        result.bonus_total = round(bonus_total, 1)

        # 6. 生成结构化反馈（issues + thinking_check + 兼容 strengths/weaknesses）
        self._generate_feedback(result, submission)

        return result

    # --------------------------------------------------------------
    # 各 grading_method 打分
    # --------------------------------------------------------------
    def _grade_compilation(self, submission: ProcessedSubmission, cat: Dict) -> Optional[CategoryScore]:
        """build：真实编译检查。无源码返回 None（由调用方记 0 分）。"""
        if not submission.source_path or not submission.project_info:
            return None

        max_points = cat.get('points', 10)
        build_result = self.build_checker.check_build(
            submission.source_path,
            f"{submission.student_id}-{submission.name}"
        )

        if build_result.status == BuildStatus.SUCCESS:
            earned_points = max_points
            feedback = "编译通过"
        elif build_result.status == BuildStatus.SKIPPED:
            # 工具链缺失（非学生责任）：本类记 0 分，但由 grade_submission 汇总时排除出
            # 总分与等级基数（按可评类别折算）。不用「无法编译」措辞以免误导。
            earned_points = 0
            feedback = "已跳过：本机未安装 make / arm-none-eabi-gcc（不代表代码无法编译）"
        elif build_result.status == BuildStatus.FAILED:
            # 编译失败一律 0 分。error_count 来自 GCC 诊断正则，链接器等错误不会被匹配
            # （error_count==0），旧实现据此判"编译通过但有警告"给 50%，把硬失败误判为通过。
            # 纯警告的构建状态为 SUCCESS，已在上面拿满分；警告不应再降低编译分。
            earned_points = 0
            if build_result.error_count:
                feedback = f"编译失败，{build_result.error_count}个错误"
            else:
                feedback = f"编译失败: {build_result.error_message or '未识别错误（可能为链接错误）'}"
        else:
            earned_points = 0
            feedback = f"无法编译: {build_result.error_message}"

        return CategoryScore(
            category_id=cat['id'],
            category_name=cat.get('name', '编译检查'),
            max_points=max_points,
            earned_points=round(earned_points, 1),
            details=[{
                'build_result': build_result,
                'feedback': feedback,
                'error_count': build_result.error_count,
                'warning_count': build_result.warning_count,
                'error_message': build_result.error_message or '',
            }]
        )

    def _grade_conditional(self, cat: Dict, is_leader: bool) -> CategoryScore:
        """conditional 类别（如组长加分）：满足条件得满分，否则 0。

        组长信息来自报告文本（detect_team_leader）；报告未声明组长则该组无组长、不加分。
        该类别通常为 points_outside_base，earned 会被计入 bonus_total，不影响百分制基数。
        """
        max_points = cat.get('points', 0)
        condition = cat.get('condition', '')
        if condition == 'is_team_leader':
            if is_leader:
                earned = float(max_points)
                feedback = f'报告声明担任组长，加 {max_points} 分'
            else:
                earned = 0.0
                feedback = '报告未声明为组长，不加分'
        else:
            earned = 0.0
            feedback = f'未知条件: {condition}'
        return CategoryScore(
            category_id=cat['id'],
            category_name=cat.get('name', cat['id']),
            max_points=max_points,
            earned_points=round(earned, 1),
            details=[{'feedback': feedback, 'is_leader': is_leader, 'condition': condition}]
        )

    def _grade_code_quality(self, submission: ProcessedSubmission, cat: Dict) -> Optional[CategoryScore]:
        """code_analysis：真实源码静态分析（优先），否则报告代码块；都没有返回 None。"""
        code_to_analyze = ""
        if submission.source_path and submission.project_info:
            for main_file in submission.project_info.main_files:
                try:
                    code_to_analyze += main_file.read_text(encoding='utf-8', errors='ignore') + "\n\n"
                except Exception:
                    pass
        if not code_to_analyze and submission.code_blocks:
            code_to_analyze = "\n\n".join(submission.code_blocks)
        if not code_to_analyze.strip():
            return None

        max_points = cat.get('points', 20)
        if not self.code_analyzer:
            return None

        try:
            analysis_result = self.code_analyzer.analyze(code_to_analyze)
            earned_points = (analysis_result.total_score / 100) * max_points

            # 结构化代码问题（带行号/严重度/建议），供直击式反馈
            issue_dicts = [
                {
                    'severity': i.severity.value,
                    'category': i.category,
                    'message': i.message,
                    'line': i.line_number,
                    'suggestion': i.suggestion,
                }
                for i in analysis_result.issues
            ]

            return CategoryScore(
                category_id=cat['id'],
                category_name=cat.get('name', '代码质量'),
                max_points=max_points,
                earned_points=round(earned_points, 1),
                details=[{
                    'analysis': {
                        'total_score': analysis_result.total_score,
                        'strengths': analysis_result.strengths,
                        'issues': issue_dicts,
                        'issue_count': len(analysis_result.issues),
                    },
                    'feedback': f"代码质量得分: {analysis_result.total_score}/100"
                }]
            )
        except Exception as e:
            print(f"警告: 代码分析失败: {e}")
            return None

    def _grade_source_check(self, submission: ProcessedSubmission, cat: Dict) -> Optional[CategoryScore]:
        """source_check：扫描源码命中禁止模式（如 HAL_Delay），按命中数扣分。

        任务书要求全部使用基于 HAL_GetTick() 的非阻塞实现，禁止 HAL_Delay()。
        遍历工程内所有源/头文件（ProjectInfo.source_files + header_files），
        按 forbid_patterns（正则）统计命中并计分。
        """
        if not submission.source_path or not submission.project_info:
            return None

        max_points = cat.get('points', 10)
        patterns = cat.get('forbid_patterns', [r'HAL_Delay\s*\('])
        penalty_per_hit = cat.get('penalty_per_hit', 5)
        # 防爆：单文件读取上限与扫描文件数上限
        MAX_FILES = 80
        MAX_FILE_BYTES = 512 * 1024

        compiled = []
        for p in patterns:
            try:
                compiled.append(re.compile(p))
            except re.error:
                continue
        if not compiled:
            return None

        violations = []  # [{file, line, match}]
        files = list(getattr(submission.project_info, 'source_files', [])) \
              + list(getattr(submission.project_info, 'header_files', []))
        for f in files[:MAX_FILES]:
            try:
                if f.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = f.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for ln, line in enumerate(text.splitlines(), start=1):
                for rx in compiled:
                    for m in rx.finditer(line):
                        violations.append({
                            'file': getattr(f, 'name', str(f)),
                            'line': ln,
                            'match': m.group(0),
                        })

        hit_count = len(violations)
        if hit_count == 0:
            earned = float(max_points)
            feedback = "未发现 HAL_Delay 调用，符合非阻塞要求"
        else:
            earned = max(0.0, max_points - hit_count * penalty_per_hit)
            sample = ", ".join(f"{v['file']}:{v['line']}" for v in violations[:3])
            more = "…" if hit_count > 3 else ""
            feedback = (f"发现 {hit_count} 处 HAL_Delay 调用（{sample}{more}），"
                        "违反非阻塞要求，需改用基于 HAL_GetTick() 的非阻塞实现")

        return CategoryScore(
            category_id=cat['id'],
            category_name=cat.get('name', '源码检查'),
            max_points=max_points,
            earned_points=round(earned, 1),
            details=[{
                'violations': violations[:20],
                'hit_count': hit_count,
                'feedback': feedback,
            }]
        )

    def _category_from_rubric_grader(self, rg_result, cat: Dict, submission: ProcessedSubmission) -> CategoryScore:
        """keyword/manual：从 RubricGrader 结果映射为引擎 CategoryScore。"""
        max_points = cat.get('points', 0)
        if rg_result is None or not submission.report_text:
            return CategoryScore(
                category_id=cat['id'],
                category_name=cat.get('name', cat['id']),
                max_points=max_points,
                earned_points=0.0,
                details=[{'feedback': '未提交报告或无正文，无法评分', 'criteria_scores': []}]
            )

        rg_cs = rg_result.category_scores.get(cat['id'])
        if rg_cs is None:
            return CategoryScore(
                category_id=cat['id'],
                category_name=cat.get('name', cat['id']),
                max_points=max_points,
                earned_points=0.0,
                details=[{'feedback': '该类别未被 RubricGrader 评分', 'criteria_scores': []}]
            )

        criteria_scores = [self._rg_criterion_to_dict(c) for c in rg_cs.criteria_scores]
        return CategoryScore(
            category_id=cat['id'],
            category_name=cat.get('name', rg_cs.name),
            max_points=max_points,
            earned_points=round(rg_cs.points_earned, 1),
            details=[{
                'feedback': '; '.join(rg_cs.feedback) if rg_cs.feedback else '',
                'criteria_scores': criteria_scores,
                'percentage': rg_cs.percentage,
            }]
        )

    # --------------------------------------------------------------
    # 反馈生成（结构化 issues + thinking_check）
    # --------------------------------------------------------------
    def _generate_feedback(self, result: GradingResult, submission: ProcessedSubmission):
        """构建结构化 issues 与 thinking_check，并填充兼容的 strengths/weaknesses。"""
        ref = (self.rubric or {}).get('reference_answers', {})
        issues: List[Dict] = []

        for cs in result.category_scores:
            cat = self._rubric_category(cs.category_id) or {}
            method = cat.get('grading_method', 'keyword')
            lost = round(cs.max_points - cs.earned_points, 1)

            if method == 'build':
                br = cs.details[0].get('build_result') if cs.details else None
                if br is not None and getattr(br, 'status', None) == BuildStatus.SKIPPED:
                    # 工具链缺失（非学生责任）：不计为失分错误项；编译行已用灰色 + 注释说明，
                    # 且 grade_submission 已把该类排除出总分。避免红色「无法编译」误导学生。
                    continue
                if cs.earned_points < cs.max_points and cs.details:
                    d = cs.details[0]
                    issues.append({
                        'type': 'build',
                        'category': cs.category_name,
                        'criterion': '编译',
                        'points_lost': lost,
                        'severity': 'error' if cs.earned_points == 0 else 'warning',
                        'message': d.get('feedback', '编译未通过'),
                        'detail': d.get('error_message', ''),
                        'expected': '工程应能通过 arm-none-eabi-gcc / make 编译，0 error',
                        'fix': '根据编译错误修正语法/链接；缺少源码工程则需补交。',
                    })
            elif method == 'code_analysis' and cs.details:
                analysis = cs.details[0].get('analysis', {}) or {}
                for ci in (analysis.get('issues') or [])[:8]:
                    issues.append({
                        'type': 'code',
                        'category': cs.category_name,
                        'criterion': ci.get('category', '代码问题'),
                        'points_lost': 0,  # 单条 issue 不单独计分，整体已反映在得分率
                        'severity': ci.get('severity', 'info'),
                        'message': ci.get('message', ''),
                        'line': ci.get('line', 0),
                        'fix': ci.get('suggestion', ''),
                        'expected': '',
                    })
            elif method == 'source_check':
                d = cs.details[0] if cs.details else {}
                if d.get('hit_count', 0) > 0:
                    issues.append({
                        'type': 'source_check',
                        'category': cs.category_name,
                        'criterion': 'HAL_Delay 禁用',
                        'points_lost': lost,
                        'severity': 'error',
                        'message': d.get('feedback', '源码含 HAL_Delay 调用'),
                        'detail': '; '.join(f"{v['file']}:{v['line']}" for v in d.get('violations', [])),
                        'expected': '全部使用基于 HAL_GetTick() 的非阻塞延时，禁止 HAL_Delay()',
                        'fix': '将 HAL_Delay(...) 改为基于 HAL_GetTick() 差值判定的非阻塞写法',
                    })
            else:  # keyword/manual：逐准则失分
                criteria_scores = (cs.details[0].get('criteria_scores') if cs.details else []) or []
                for crit in criteria_scores:
                    p_lost = round(crit.get('points_possible', 0) - crit.get('points_earned', 0), 1)
                    if p_lost <= 0:
                        continue
                    issues.append({
                        'type': 'criterion',
                        'category': cs.category_name,
                        'category_id': cs.category_id,
                        'criterion': crit.get('description', ''),
                        'missing_keywords': crit.get('missing_keywords', []),
                        'points_lost': p_lost,
                        'severity': 'warning',
                        'message': f"未充分体现：{', '.join(crit.get('missing_keywords', [])) or '相关关键词缺失'}",
                        'expected': self._expected_answer(cs.category_id, crit.get('description', ''), ref),
                        'fix': (f"此处可回收 {p_lost:g} 分：围绕「{crit.get('description', '')}」"
                                "把原理/做法/数据写清写准即可拿回（缺失关键词见上）。"),
                    })

        # 思考题核对：依据校验器在"七、思考题"章节内检测到的题号（避免正文其它编号误判）+ 参考答案
        result.thinking_check = self._build_thinking_check(result.validation_report, ref)

        result.issues = issues

        # 兼容旧字段：strengths/weaknesses/suggestions（供尚未迁移的消费者）
        result.weaknesses = [
            f"{it.get('category', '')}：{it.get('message', '')}"
            for it in issues if it.get('severity') in ('error', 'warning')
        ][:10]
        result.suggestions = [it.get('fix', '') for it in issues if it.get('fix')][:10]
        result.strengths = [
            cs.category_name for cs in result.category_scores
            if cs.max_points > 0 and cs.earned_points >= cs.max_points
        ]

    def _build_thinking_check(self, validation_report, ref: Dict) -> List[Dict]:
        """逐题 Q1~Q7：是否作答（依据校验器在七、章节的检测）+ 参考答案方向。"""
        # rubric 声明 thinking_check=false（如综合项目思考题为选做）时不生成该表
        if not (self.rubric or {}).get('thinking_check', True):
            return []
        answers = ref.get('thinking_questions', {}) if isinstance(ref, dict) else {}
        missing = set()
        if validation_report is not None:
            missing = set(validation_report.missing_questions or [])
        return [
            {
                'id': f'Q{i}',
                'answered': f'Q{i}' not in missing,
                'expected': answers.get(f'Q{i}', ''),
            }
            for i in range(1, 8)
        ]

    def _expected_answer(self, category_id: str, criterion_desc: str, ref: Dict) -> str:
        """按类别/准则启发式回填参考答案（让反馈'正确应为'更具体）。"""
        if not isinstance(ref, dict):
            return ''
        desc = criterion_desc or ''
        try:
            if category_id == 'principle_understanding':
                if '原理' in desc:
                    parts = [f"消抖：{ref.get('debouncing','')}", f"中断：{ref.get('interrupt_config','')}"]
                    return '；'.join(p for p in parts if p)
            if category_id == 'completion':
                if '引脚' in desc or '硬件' in desc:
                    gp = ref.get('gpio_pins', {})
                    if gp:
                        return 'GPIO：' + '，'.join(f"{k}={v}" for k, v in gp.items())
                if '现象' in desc or '结果' in desc:
                    gs = ref.get('gear_states', {})
                    if gs:
                        return '档位 LED：' + '，'.join(f"{k}:{v}" for k, v in gs.items())
            if category_id == 'report_quality' and '思考题' in desc:
                tq = ref.get('thinking_questions', {})
                if tq:
                    return '应逐题作答 Q1~Q7，参考方向见评分反馈「思考题核对」'
        except Exception:
            return ''
        return ''

    # --------------------------------------------------------------
    # 工具
    # --------------------------------------------------------------
    def _rubric_category(self, cat_id: str) -> Optional[Dict]:
        for c in (self.rubric or {}).get('categories', []):
            if c.get('id') == cat_id:
                return c
        return None

    @staticmethod
    def _rg_category_to_dict(cs) -> Dict:
        return {
            'category_id': cs.category_id,
            'name': cs.name,
            'points_earned': cs.points_earned,
            'points_possible': cs.points_possible,
            'percentage': cs.percentage,
            'feedback': list(cs.feedback),
            'criteria_scores': [AutoGradingEngine._rg_criterion_to_dict(c) for c in cs.criteria_scores],
        }

    @staticmethod
    def _rg_criterion_to_dict(c) -> Dict:
        return {
            'criterion_id': c.criterion_id,
            'description': c.description,
            'points_earned': c.points_earned,
            'points_possible': c.points_possible,
            'matched_keywords': list(c.matched_keywords),
            'missing_keywords': list(getattr(c, 'missing_keywords', [])),
            'feedback': c.feedback,
        }

    def _calculate_grade(self, score: float, grading_scale: Dict) -> str:
        # 半开区间匹配（按 min 降序），消除 B.max=89.9/A.min=90 之类边界缝隙；
        # 与 RubricGrader._calculate_grade 语义保持一致。
        for grade, info in sorted(grading_scale.items(), key=lambda x: x[1]['min'], reverse=True):
            if score >= info['min']:
                return grade
        return 'F'

    def _calculate_grade_default(self, score: float, max_score: float) -> str:
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'

    # --------------------------------------------------------------
    # 批量与班级报告
    # --------------------------------------------------------------
    def batch_grade(self, submissions: List[ProcessedSubmission]) -> List[GradingResult]:
        results = []
        for i, submission in enumerate(submissions):
            print(f"评分 ({i+1}/{len(submissions)}): {submission.student_id}-{submission.name}")
            result = self.grade_submission(submission)
            results.append(result)
            print(f"  得分: {result.total_score:.1f}/{result.max_score:.1f} (加分{result.bonus_total:.0f}) ({result.grade})")
        return results

    def generate_class_report(self, results: List[GradingResult]) -> Dict:
        if not results:
            return {}

        total = len(results)
        scores = [r.total_score for r in results]

        grade_distribution = {}
        for r in results:
            grade_distribution[r.grade] = grade_distribution.get(r.grade, 0) + 1

        category_stats = {}
        for result in results:
            for cat_score in result.category_scores:
                cat_id = cat_score.category_id
                if cat_id not in category_stats:
                    category_stats[cat_id] = {
                        'name': cat_score.category_name,
                        'total_points': 0,
                        'max_points': 0,
                        'count': 0
                    }
                category_stats[cat_id]['total_points'] += cat_score.earned_points
                category_stats[cat_id]['max_points'] += cat_score.max_points
                category_stats[cat_id]['count'] += 1

        for cat_id, stats in category_stats.items():
            if stats['count'] > 0:
                stats['average'] = stats['total_points'] / stats['count']
                stats['max_average'] = stats['max_points'] / stats['count']

        return {
            'total_students': total,
            'average_score': sum(scores) / total if total > 0 else 0,
            'max_score': results[0].max_score if results else 0,
            'grade_distribution': grade_distribution,
            'category_stats': category_stats,
            'individual_results': [
                {
                    'student_id': r.student_id,
                    'name': r.name,
                    'score': r.total_score,
                    'bonus': r.bonus_total,
                    'grade': r.grade
                }
                for r in results
            ]
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='整合评分引擎')
    parser.add_argument('class_name', type=str, help='班级名称')
    parser.add_argument('experiment_id', type=str, help='实验ID')
    parser.add_argument('--rubric', type=Path, help='评分标准文件路径')
    parser.add_argument('--base-dir', type=Path, default='data/teaching/2026-春季/', help='基础目录')

    args = parser.parse_args()

    from .submission_processor import SubmissionProcessor

    processor = SubmissionProcessor(args.base_dir)
    engine = AutoGradingEngine(rubric_path=args.rubric)

    submissions = processor.process_class_submissions(args.class_name, args.experiment_id)
    print(f"找到 {len(submissions)} 个提交")

    results = engine.batch_grade(submissions)
    class_report = engine.generate_class_report(results)

    print()
    print("=" * 60)
    print("班级报告")
    print("=" * 60)
    print(f"平均分: {class_report['average_score']:.1f}")
    print(f"等级分布: {class_report['grade_distribution']}")


if __name__ == '__main__':
    main()
