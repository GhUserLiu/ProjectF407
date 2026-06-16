#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
编译检查器
Build Checker

提供批量编译检查功能：
- 支持STM32CubeMX项目（使用项目内Makefile）
- 支持Keil项目（使用UV4命令行，可选）
- 解析编译输出，提取错误和警告
- 生成编译检查报告
"""

import re
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from .config import AutoGradingConfig


class BuildStatus(Enum):
    """编译状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    ERROR = "error"  # 工具链错误
    NOT_FOUND = "not_found"  # 项目文件未找到
    SKIPPED = "skipped"  # 跳过（例如：不支持的类型）


@dataclass
class BuildIssue:
    """编译问题"""
    severity: str  # error, warning, note
    file: str     # 文件路径
    line: int     # 行号
    column: int   # 列号
    message: str  # 问题信息


@dataclass
class BuildResult:
    """编译结果"""
    status: BuildStatus
    project_name: str
    project_path: Path
    success: bool
    duration: float = 0.0  # 编译耗时（秒）
    error_count: int = 0
    warning_count: int = 0
    issues: List[BuildIssue] = field(default_factory=list)
    output: str = ""  # 完整输出
    error_message: str = ""  # 错误信息（如果失败）


class BuildChecker:
    """编译检查器"""

    # GCC编译输出模式
    GCC_ERROR_PATTERN = re.compile(
        r'([^:]+):(\d+):(\d+):\s+(error|warning|note):\s+(.+)'
    )

    # Keil编译输出模式
    KEIL_ERROR_PATTERN = re.compile(
        r'(.+)\((\d+)\):\s+(Error|Warning)\s+(\d+):\s+(.+)'
    )

    def __init__(self, config: Optional[AutoGradingConfig] = None):
        """
        初始化编译检查器

        Args:
            config: 配置对象，如果为None则使用默认配置
        """
        self.config = config or AutoGradingConfig()

        # 检查工具链
        self._check_toolchain()

    def _check_toolchain(self):
        """检查工具链是否可用"""
        # 检查make
        if not shutil.which(self.config.toolchain.make_path):
            raise RuntimeError(f"Make命令不可用: {self.config.toolchain.make_path}")

        # 检查arm-none-eabi-gcc
        if not shutil.which(f"{self.config.toolchain.arm_none_eabi_prefix}gcc"):
            print(f"警告: arm-none-eabi-gcc不可用，仅支持Keil项目")

        # 检查Keil（如果启用）
        if self.config.toolchain.keil_enabled:
            if not Path(self.config.toolchain.keil_uv4_path).exists():
                print(f"警告: Keil UV4不可用: {self.config.toolchain.keil_uv4_path}")

    def check_build(
        self,
        project_path: Path,
        project_name: Optional[str] = None,
        toolchain: str = 'auto'
    ) -> BuildResult:
        """
        检查单个项目的编译状态

        Args:
            project_path: 项目路径
            project_name: 项目名称（可选）
            toolchain: 工具链类型（auto, gcc, keil）

        Returns:
            编译结果
        """
        import time

        if not project_path.exists():
            return BuildResult(
                status=BuildStatus.NOT_FOUND,
                project_name=project_name or project_path.name,
                project_path=project_path,
                success=False,
                error_message="项目路径不存在"
            )

        start_time = time.time()

        # 自动检测项目类型
        if toolchain == 'auto':
            toolchain = self._detect_project_type(project_path)

        try:
            if toolchain == 'gcc':
                result = self._check_gcc_build(project_path, project_name)
            elif toolchain == 'keil':
                result = self._check_keil_build(project_path, project_name)
            else:
                result = BuildResult(
                    status=BuildStatus.SKIPPED,
                    project_name=project_name or project_path.name,
                    project_path=project_path,
                    success=False,
                    error_message=f"不支持的工具链: {toolchain}"
                )
        except subprocess.TimeoutExpired:
            result = BuildResult(
                status=BuildStatus.TIMEOUT,
                project_name=project_name or project_path.name,
                project_path=project_path,
                success=False,
                error_message="编译超时"
            )
        except Exception as e:
            result = BuildResult(
                status=BuildStatus.ERROR,
                project_name=project_name or project_path.name,
                project_path=project_path,
                success=False,
                error_message=str(e)
            )

        result.duration = time.time() - start_time
        return result

    def batch_check(
        self,
        projects: List[Tuple[Path, str]],
        toolchain: str = 'auto'
    ) -> Dict[str, BuildResult]:
        """
        批量检查多个项目

        Args:
            projects: (项目路径, 项目名称)列表
            toolchain: 工具链类型

        Returns:
            项目名称 -> 编译结果的字典
        """
        results = {}

        for project_path, project_name in projects:
            result = self.check_build(project_path, project_name, toolchain)
            results[project_name] = result

            # 打印进度
            status_icon = "✓" if result.success else "✗"
            print(f"  {status_icon} {project_name}: {result.status.value}")

        return results

    def _detect_project_type(self, project_path: Path) -> str:
        """
        检测项目类型

        Returns:
            'gcc' 或 'keil'
        """
        # 检查是否有Makefile（CubeMX项目）
        if (project_path / "Makefile").exists():
            return 'gcc'

        # 检查是否有MDK-ARM目录（CubeMX生成的Keil项目）
        if (project_path / "MDK-ARM").exists():
            # 检查是否有.uvprojx文件
            uvprojx_files = list((project_path / "MDK-ARM").glob("*.uvprojx"))
            if uvprojx_files:
                return 'gcc'  # CubeMX的Keil项目也可以用GCC

        # 检查是否有.uvprojx文件（纯Keil项目）
        uvprojx_files = list(project_path.glob("*.uvprojx"))
        if uvprojx_files:
            if self.config.toolchain.keil_enabled:
                return 'keil'
            else:
                return 'gcc'  # 尝试用GCC

        # 默认使用GCC
        return 'gcc'

    def _check_gcc_build(
        self,
        project_path: Path,
        project_name: Optional[str] = None
    ) -> BuildResult:
        """
        使用GCC工具链检查编译

        Args:
            project_path: 项目路径
            project_name: 项目名称

        Returns:
            编译结果
        """
        name = project_name or project_path.name

        # 检查是否有Makefile
        makefile = project_path / "Makefile"
        if not makefile.exists():
            # 尝试查找CubeMX的MDK-ARM目录
            mdk_dir = project_path / "MDK-ARM"
            if mdk_dir.exists():
                makefile = mdk_dir / "Makefile"
            else:
                return BuildResult(
                    status=BuildStatus.NOT_FOUND,
                    project_name=name,
                    project_path=project_path,
                    success=False,
                    error_message="未找到Makefile"
                )

        # 调用make命令
        cmd = [
            self.config.toolchain.make_path,
            '-C', str(makefile.parent),
            'clean',
            'all'
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.toolchain.build_timeout,
                cwd=str(makefile.parent)
            )
        except subprocess.TimeoutExpired:
            raise

        # 解析输出
        output = result.stdout + result.stderr
        issues = self._parse_gcc_output(output)

        # 统计错误和警告
        error_count = sum(1 for i in issues if i.severity == 'error')
        warning_count = sum(1 for i in issues if i.severity == 'warning')

        # 判断是否成功
        success = result.returncode == 0 and error_count == 0

        return BuildResult(
            status=BuildStatus.SUCCESS if success else BuildStatus.FAILED,
            project_name=name,
            project_path=project_path,
            success=success,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            output=output
        )

    def _check_keil_build(
        self,
        project_path: Path,
        project_name: Optional[str] = None
    ) -> BuildResult:
        """
        使用Keil UV4检查编译

        Args:
            project_path: 项目路径
            project_name: 项目名称

        Returns:
            编译结果
        """
        name = project_name or project_path.name

        if not self.config.toolchain.keil_enabled:
            return BuildResult(
                status=BuildStatus.ERROR,
                project_name=name,
                project_path=project_path,
                success=False,
                error_message="Keil工具链未启用"
            )

        # 查找.uvprojx文件
        uvprojx_files = list(project_path.glob("*.uvprojx"))
        if not uvprojx_files:
            mdk_dir = project_path / "MDK-ARM"
            if mdk_dir.exists():
                uvprojx_files = list(mdk_dir.glob("*.uvprojx"))

        if not uvprojx_files:
            return BuildResult(
                status=BuildStatus.NOT_FOUND,
                project_name=name,
                project_path=project_path,
                success=False,
                error_message="未找到.uvprojx文件"
            )

        uvprojx_file = uvprojx_files[0]

        # 调用Keil UV4命令
        cmd = [
            self.config.toolchain.keil_uv4_path,
            '-r',  # 重建
            '-j0',  # 并行编译
            '-b',  # 批处理模式
            str(uvprojx_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.toolchain.build_timeout
            )
        except subprocess.TimeoutExpired:
            raise

        # 解析输出
        output = result.stdout + result.stderr
        issues = self._parse_keil_output(output)

        # 统计错误和警告
        error_count = sum(1 for i in issues if i.severity == 'error')
        warning_count = sum(1 for i in issues if i.severity == 'warning')

        # 判断是否成功（Keil返回0表示成功）
        success = result.returncode == 0 and error_count == 0

        return BuildResult(
            status=BuildStatus.SUCCESS if success else BuildStatus.FAILED,
            project_name=name,
            project_path=project_path,
            success=success,
            error_count=error_count,
            warning_count=warning_count,
            issues=issues,
            output=output
        )

    def _parse_gcc_output(self, output: str) -> List[BuildIssue]:
        """解析GCC编译输出"""
        issues = []

        for line in output.split('\n'):
            match = self.GCC_ERROR_PATTERN.search(line)
            if match:
                file, line_no, col, severity, message = match.groups()
                issues.append(BuildIssue(
                    severity=severity,
                    file=file,
                    line=int(line_no),
                    column=int(col),
                    message=message.strip()
                ))

        return issues

    def _parse_keil_output(self, output: str) -> List[BuildIssue]:
        """解析Keil编译输出"""
        issues = []

        for line in output.split('\n'):
            match = self.KEIL_ERROR_PATTERN.search(line)
            if match:
                file, line_no, severity, code, message = match.groups()
                issues.append(BuildIssue(
                    severity=severity.lower(),
                    file=file,
                    line=int(line_no),
                    column=0,
                    message=f"{code}: {message}".strip()
                ))

        return issues

    def generate_report(self, results: Dict[str, BuildResult]) -> str:
        """
        生成编译检查报告

        Args:
            results: 编译结果字典

        Returns:
            报告文本
        """
        lines = [
            "=" * 70,
            "编译检查报告",
            "=" * 70,
            "",
            f"总项目数: {len(results)}",
            f"编译成功: {sum(1 for r in results.values() if r.success)}",
            f"编译失败: {sum(1 for r in results.values() if not r.success and r.status == BuildStatus.FAILED)}",
            f"跳过/错误: {sum(1 for r in results.values() if r.status in [BuildStatus.ERROR, BuildStatus.NOT_FOUND, BuildStatus.SKIPPED])}",
            "",
        ]

        # 详细结果
        lines.extend([
            "详细结果:",
            "-" * 70,
        ])

        for name, result in results.items():
            status_icon = "✓" if result.success else "✗"
            lines.append(f"{status_icon} {name}: {result.status.value}")

            if result.error_count > 0:
                lines.append(f"    错误: {result.error_count}")
            if result.warning_count > 0:
                lines.append(f"    警告: {result.warning_count}")
            if result.error_message:
                lines.append(f"    错误信息: {result.error_message}")

            # 显示前3个错误
            errors = [i for i in result.issues if i.severity == 'error'][:3]
            for error in errors:
                lines.append(f"      {error.file}:{error.line}: {error.message}")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='编译检查器')
    parser.add_argument('project', type=Path, help='项目路径')
    parser.add_argument('--name', type=str, help='项目名称')
    parser.add_argument('--toolchain', choices=['auto', 'gcc', 'keil'], default='auto', help='工具链类型')

    args = parser.parse_args()

    checker = BuildChecker()

    result = checker.check_build(args.project, args.name, args.toolchain)

    print(f"项目: {result.project_name}")
    print(f"状态: {result.status.value}")
    print(f"成功: {'是' if result.success else '否'}")

    if result.error_count > 0:
        print(f"错误数: {result.error_count}")
    if result.warning_count > 0:
        print(f"警告数: {result.warning_count}")

    if result.issues:
        print("\n问题详情:")
        for issue in result.issues[:10]:  # 只显示前10个
            print(f"  [{issue.severity}] {issue.file}:{issue.line}: {issue.message}")


if __name__ == '__main__':
    main()
