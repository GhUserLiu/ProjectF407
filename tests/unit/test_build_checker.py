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


class TestGccBuildCommand:
    """验证 _check_gcc_build 下发的 make 命令形态。

    回归：旧实现 ``make -C <dir>``，-C 收到的 Windows 反斜杠路径会被 MSYS make 解析坏。
    修复后应仅 ``['make', 'clean', 'all']``，并依赖 cwd（已设为 makefile.parent）。
    """

    def test_make_cmd_has_no_dash_c(self, tmp_path, monkeypatch):
        # 准备一个含 Makefile 的工程根
        proj = tmp_path / "proj"
        proj.mkdir()
        (proj / "Makefile").write_text("all:\n", encoding="utf-8")

        captured = {}

        class _FakeCompleted:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd, *args, **kwargs):
            captured["cmd"] = list(cmd)
            captured["cwd"] = kwargs.get("cwd")
            return _FakeCompleted()

        # 真实工具链是否在 PATH 不影响本测试：强制视为可用，跳过 SKIPPED 分支
        import tools.auto_grading.build_checker as bc
        monkeypatch.setattr(bc.subprocess, "run", fake_run)

        checker = BuildChecker()
        monkeypatch.setattr(checker, "make_available", True)
        monkeypatch.setattr(checker, "gcc_available", True)

        result = checker.check_build(proj, "test-proj")

        # 命令不得含 -C，也不得带路径参数
        assert captured["cmd"] == ["make", "clean", "all"]
        assert "-C" not in captured["cmd"]
        # cwd 仍指向 Makefile 所在目录（make 据此定位 Makefile）
        assert captured["cwd"] == str(proj)
        # returncode=0 且无 error → 编译成功
        assert result.status == BuildStatus.SUCCESS
        assert result.success is True
