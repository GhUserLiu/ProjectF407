#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生端自检编排核心
SelfChecker

单份提交的「编排器」：构建 ProcessedSubmission（绕开教师端对班级压缩包的整理
与文件名硬约束），复用教师端 auto_grading 的读报告 / 校验 / rubric 评分能力。

流水线（单份，无班级整理、无查重）：
    选报告(.docx/.doc/.pdf) + 选源码(目录或 zip) + 身份 + 实验
        → 读报告文本 / 抽代码块 / 分析工程（zip 先安全解压到 tempdir）
        → AutoGradingEngine.grade_submission（内部已含 SubmissionValidator 校验）
        → 返回 SelfCheckResult

不直接调 SubmissionValidator——评分引擎内部已校验并把结果挂在
GradingResult.validation_report，直接复用避免二次校验（口径一致）。
"""

import atexit
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from tools.auto_grading.config import AutoGradingConfig
from tools.auto_grading.submission_processor import (
    SubmissionProcessor, ProcessedSubmission,
)
from tools.auto_grading.grading_engine import AutoGradingEngine, GradingResult
from tools.auto_grading.submission_validator import ValidationReport
from tools.auto_grading.build_checker import BuildStatus
from tools.security.zip_validator import safe_extract_zip, ZipValidationError, ZipLimits

from .id_card import StudentIdentity
from .runtime import bundle_root


# 学生端源码包解压限制：与教师端 submission_organizer 的 source_limits 保持一致。
# 学生提交的 CubeMX 工程常含完整 HAL Drivers / CMSIS / 构建产物，文件数动辄过千，
# 默认的 1000 上限会把正常工程误判为 zip 炸弹（曾出现 1270>1000 拒收）。
_SOURCE_LIMITS = ZipLimits(
    max_file_count=5000,
    max_outer_size=500 * 1024 * 1024,   # 500MB（学生可能包含大型库文件）
    max_inner_size=200 * 1024 * 1024,   # 200MB
)


@dataclass
class SelfCheckResult:
    """单份提交自检结果。"""
    submission: ProcessedSubmission
    validation: ValidationReport          # = grading.validation_report（复用）
    grading: GradingResult
    temp_dirs: List[Path] = field(default_factory=list)
    toolchain: dict = field(default_factory=lambda: {"make": False, "gcc": False})
    experiment_code: str = ""
    warnings: List[str] = field(default_factory=list)  # 非致命降级提示（如源码包无法解压）


class SelfChecker:
    """单份提交编排器（学生端）。"""

    def __init__(self, config: Optional[AutoGradingConfig] = None):
        # 冻结态下用 bundle_root()（资源在解包目录），开发态下 bundle_root()==cwd
        self.config = config or AutoGradingConfig(project_root=bundle_root())
        # base_dir 仅满足 SubmissionProcessor 构造，下方复用的三个方法均不依赖它
        self._processor = SubmissionProcessor(self.config.teaching_dir)

    # ----------------------------------------------------------
    # 主入口
    # ----------------------------------------------------------
    def run(
        self,
        report_path: Path,
        source_path: Optional[Path],
        identity: StudentIdentity,
        experiment_code: str,
    ) -> SelfCheckResult:
        """对单份提交执行「检测 + 自评」。

        Args:
            report_path: 实验报告路径（.docx 佳；.doc/.pdf 会降级）
            source_path: 源代码——目录或 .zip；可为 None
            identity: 学生身份（班级/学号/姓名）
            experiment_code: 实验 id（如 07-car-gear），用于定位 rubric

        Returns:
            SelfCheckResult

        Raises:
            原样向上抛出；抛出前会清理本调用创建的所有 tempdir。
        """
        report_path = Path(report_path)
        temp_dirs: List[Path] = []
        warnings: List[str] = []
        try:
            # 1. 读报告 + 抽代码块（复用教师端，无文件名依赖）
            report_text = self._processor._read_report(report_path)
            code_blocks = self._processor._extract_code_blocks(report_text)

            # 2. 解析源码工程（zip 安全解压到 tempdir 后分析）
            resolved_source: Optional[Path] = None
            project_info = None
            if source_path:
                src = Path(source_path)
                if src.is_file() and src.suffix.lower() == ".zip":
                    try:
                        extracted = self._extract_zip(src, temp_dirs)
                        resolved_source = self._unwrap_wrapper(extracted)
                    except ZipValidationError as e:
                        # 解压失败（超限/损坏/恶意）不阻断整轮自检：降级为「无源码」，
                        # 仍可基于报告评分；warning 由 worker 记入日志供学生知情。
                        warnings.append(
                            f"源码压缩包无法解压已忽略（{e}）；"
                            "编译/代码质量将基于报告内容或记为缺失。"
                        )
                # 其它情况（不存在、非 zip、目录——学生端 UI 已统一为选 zip）忽略，留给校验器提示

                if resolved_source and resolved_source.exists():
                    project_info = self._processor._analyze_project(resolved_source)

            # 3. 直接构造 ProcessedSubmission（身份来自 UI，不依赖文件名）
            submission = ProcessedSubmission(
                student_id=identity.student_id,
                name=identity.name,
                class_name=identity.class_name,
                report_path=report_path,
                report_text=report_text,
                source_path=resolved_source,
                project_info=project_info,
                code_blocks=code_blocks,
            )

            # 4. 评分（引擎内部已调用 validator.validate，结果挂 validation_report）
            engine = self._build_engine(experiment_code)
            grading = engine.grade_submission(submission)
            toolchain = {
                "make": getattr(engine.build_checker, "make_available", False),
                "gcc": getattr(engine.build_checker, "gcc_available", False),
            }

            return SelfCheckResult(
                submission=submission,
                validation=grading.validation_report,
                grading=grading,
                temp_dirs=temp_dirs,
                toolchain=toolchain,
                experiment_code=experiment_code,
                warnings=warnings,
            )
        except Exception:
            # 任何异常都先清理本调用创建的 tempdir，再向上抛
            SelfChecker.cleanup(temp_dirs)
            raise

    # ----------------------------------------------------------
    # 源码 zip 处理
    # ----------------------------------------------------------
    def _extract_zip(self, zip_path: Path, temp_dirs: List[Path]) -> Path:
        """安全解压源码 zip 到临时目录。

        - mkdtemp 置于 OS temp（不放仓库，避免污染 git/体积膨胀）
        - atexit 兜底清理（Ctrl-C/关窗）；正常完成由 worker finally 清理
        - safe_extract_zip 防路径穿越/zip 炸弹
        """
        tmp = Path(tempfile.mkdtemp(prefix="student_src_"))
        temp_dirs.append(tmp)
        atexit.register(lambda: shutil.rmtree(tmp, ignore_errors=True))
        try:
            safe_extract_zip(zip_path, tmp, limits=_SOURCE_LIMITS)
        except ZipValidationError:
            # 解压失败：立即清理并从清单移除，避免后续误清理已删目录
            shutil.rmtree(tmp, ignore_errors=True)
            temp_dirs.remove(tmp)
            raise
        return tmp

    @staticmethod
    def _unwrap_wrapper(extracted_root: Path) -> Path:
        """若解压根下只有一个顶层目录且「像工程」，则下钻一层。

        常见情况：学生把整个工程打成 zip 时外面多套了一层目录。
        _analyze_project 用 rglob，即便不拆包裹也能找到文件；但拆包裹更干净，
        避免把无关兄弟文件（如 __MACOSX）卷入分析。
        """
        try:
            entries = [p for p in extracted_root.iterdir() if not p.name.startswith(".")]
        except Exception:
            return extracted_root
        if len(entries) != 1 or not entries[0].is_dir():
            return extracted_root
        candidate = entries[0]
        if SelfChecker._looks_like_project(candidate):
            return candidate
        return extracted_root

    @staticmethod
    def _looks_like_project(d: Path) -> bool:
        """目录是否像 STM32 工程：含 Makefile / Core / MDK-ARM / Drivers，
        或含 .uvprojx / 任意 .c。"""
        for marker in ("Makefile", "Core", "MDK-ARM", "Drivers"):
            if (d / marker).exists():
                return True
        try:
            if list(d.glob("*.uvprojx")):
                return True
            if list(d.glob("*.c")) or list(d.glob("*.h")):
                return True
            # 再深一层也认（Core/Src/main.c 这类）
            if any(d.rglob("*.uvprojx")) or any(d.rglob("*.c")):
                return True
        except Exception:
            pass
        return False

    # ----------------------------------------------------------
    # 引擎构造（按实验定位 rubric）
    # ----------------------------------------------------------
    def _build_engine(self, experiment_code: str) -> AutoGradingEngine:
        rubric_path = self.config.get_rubric_path(experiment_code)
        return AutoGradingEngine(
            self.config,
            rubric_path=rubric_path if rubric_path.exists() else None,
        )

    # ----------------------------------------------------------
    # 工具
    # ----------------------------------------------------------
    @staticmethod
    def cleanup(temp_dirs: List[Path]) -> None:
        """清理所有临时解压目录。"""
        for tmp in temp_dirs or []:
            try:
                shutil.rmtree(tmp, ignore_errors=True)
            except Exception:
                pass


def build_status_of(grading: GradingResult) -> Optional[BuildStatus]:
    """从评分结果抽取编译类别的 BuildStatus（供 UI 区分 SKIPPED/FAILED/SUCCESS）。

    编译类别 details[0]['build_result'] 是 BuildResult；缺失返回 None。
    """
    for cs in grading.category_scores:
        if cs.category_id == "compilation" and cs.details:
            br = cs.details[0].get("build_result")
            if br is not None and hasattr(br, "status"):
                return br.status
    return None
