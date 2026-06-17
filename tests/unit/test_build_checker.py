# -*- coding: utf-8 -*-
"""
编译检查器单元测试
Build Checker Unit Tests

由根目录诊断脚本 test_build_checker.py 重构为正式 pytest 用例。
不依赖真实 make/arm-none-eabi-gcc 工具链，仅测配置默认值与错误输出解析。
"""

import pytest

from tools.auto_grading.config import AutoGradingConfig
from tools.auto_grading.build_checker import (
    BuildChecker,
    BuildResult,
    BuildStatus,
)


class TestAutoGradingConfig:
    def test_defaults(self):
        cfg = AutoGradingConfig()
        assert cfg.toolchain.make_path == "make"
        assert cfg.toolchain.arm_none_eabi_prefix == "arm-none-eabi-"
        assert cfg.semester == "2026-春季"
        assert "07-car-gear" in cfg.project.allowed_projects

    def test_output_dir_uses_path_config(self, tmp_path):
        cfg = AutoGradingConfig(project_root=tmp_path)
        out = cfg.get_output_dir("汽服2302B班", "07-car-gear")
        assert out.parts[-1] == "grading"
        assert out == (
            tmp_path / "data" / "teaching" / "2026-春季"
            / "汽服2302B班" / "07-car-gear" / "results" / "grading"
        )


class TestBuildCheckerPatterns:
    """直接测类级正则，避免触发工具链探测。"""

    def test_gcc_error_pattern(self):
        line = "src/main.c:42:7: error: expected ';' before '}' token"
        m = BuildChecker.GCC_ERROR_PATTERN.search(line)
        assert m is not None
        assert m.group(1) == "src/main.c"
        assert m.group(2) == "42"
        assert m.group(4) == "error"
        assert "expected" in m.group(5)

    def test_gcc_warning_pattern(self):
        line = "drivers/timer.c:10:3: warning: unused variable 'x' [-Wunused-variable]"
        m = BuildChecker.GCC_ERROR_PATTERN.search(line)
        assert m is not None
        assert m.group(4) == "warning"

    def test_gcc_pattern_ignores_plain_text(self):
        assert BuildChecker.GCC_ERROR_PATTERN.search("just some log line") is None

    def test_keil_error_pattern(self):
        # Keil 模式：file(line): Error <num>: message
        line = 'main.c(57): Error 20: identifier "HAL_GPIO" is undefined'
        m = BuildChecker.KEIL_ERROR_PATTERN.search(line)
        assert m is not None
        assert m.group(1) == "main.c"
        assert m.group(2) == "57"
        assert m.group(3) == "Error"


class TestBuildResult:
    def test_success_result(self, tmp_path):
        r = BuildResult(
            status=BuildStatus.SUCCESS,
            project_name="01-turn-signal",
            project_path=tmp_path,
            success=True,
        )
        assert r.success is True
        assert r.error_count == 0
        assert r.status == BuildStatus.SUCCESS
