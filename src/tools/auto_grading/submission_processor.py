#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
提交处理器
Submission Processor

处理已整理的提交数据（reports/ 和 source/ 目录）：
- 读取实验报告内容
- 提取源代码信息
- 准备评分所需的数据结构

输入：经过 SubmissionOrganizer 处理后的标准格式目录
输出：用于评分的 ProcessedSubmission 对象列表
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

from ..security.zip_validator import safe_extract_text_from_docx
from ..security.xml_parser import extract_text_from_docx_xml
from .source_state import SourceStateClassifier


@dataclass
class ProjectInfo:
    """项目信息"""
    project_path: Path          # 项目根目录
    project_type: str          # 项目类型（cubemx, keil, simple）
    main_files: List[Path]     # 主程序文件列表
    header_files: List[Path]   # 头文件列表
    source_files: List[Path]   # 所有源文件列表
    has_makefile: bool         # 是否有Makefile
    has_uvprojx: bool          # 是否有Keil项目文件


@dataclass
class ProcessedSubmission:
    """已处理的提交"""
    student_id: str            # 学号
    name: str                  # 姓名
    class_name: str            # 班级

    # 报告信息
    report_path: Optional[Path] = None      # 报告文件路径
    report_text: str = ""                    # 报告文本内容

    # 源代码信息
    source_path: Optional[Path] = None       # 源代码目录路径
    project_info: Optional[ProjectInfo] = None  # 项目信息
    source_state: Optional[Any] = None       # 源码工程状态（SourceState）——格式问题的具体原因/改进

    # 提取的代码块（从报告中）
    code_blocks: List[str] = field(default_factory=list)

    # 元数据
    processed_at: datetime = field(default_factory=datetime.now)


# 表式布局里不该被当作姓名的角色/表头词
_ROLE_TOKENS = ("组长", "组员", "成员", "姓名", "学号", "班级", "角色", "学号 ", "分工")


def parse_team_members(
    report_text: str,
    primary_id: str,
    primary_name: str,
) -> List[Tuple[str, str]]:
    """从报告"团队成员基本信息"表解析成员，返回 [(学号, 姓名), ...]。

    综合项目报告开头通常有"一、团队信息与分工 / 团队成员基本信息"表（docx 表格抽
    出后呈竖排单元格序列：姓名\\n学号\\n班级\\n组内角色\\n<成员1>\\n<学号1>…）。
    本函数定位该章节，抽取"姓名 + 紧随的 11 位学号"对，去重并确保包含文件名里的
    组长(primary)。解析不到任何成员时回退为 [(primary_id, primary_name)]。

    Args:
        report_text: 报告正文
        primary_id: 文件名解析出的学号（通常为组长）
        primary_name: 文件名解析出的姓名

    Returns:
        [(学号, 姓名), ...]，至少 1 条。
    """
    text = report_text or ""
    # 1) 定位团队信息章节
    m = re.search(r'团队成员.{0,6}信息|团队成员基本信息|团队信息与分工|团队成员|分组|小组成员', text)
    if not m:
        return [(primary_id, primary_name)]
    section = text[m.start():]
    # 2) 截到下一子节/章节前（个人分工说明、二、…、1.2 等），避免误抓正文里的姓名+学号
    end = re.search(r'个人分工|分工说明|任务分工|\n\s*[1-9]\s*[\.、][2-9]|[\n\s][二三四五六七][、]', section)
    if end:
        section = section[:end.start()]

    # 3) 抽取 (姓名, 11位学号)：姓名（2-5 汉字）+ 空白 + 11 位学号（首数字非 0）
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for mm in re.finditer(r'([一-龥]{2,5})\s*([1-9]\d{10})', section):
        name, sid = mm.group(1), mm.group(2)
        # 剥离可能的角色前缀（如"组长张三"），并跳过纯角色/表头词
        for tok in _ROLE_TOKENS:
            if name.startswith(tok):
                name = name[len(tok):]
                break
        if not name or name in _ROLE_TOKENS or len(name) > 5:
            continue
        if sid in seen:
            continue
        seen.add(sid)
        pairs.append((sid, name))

    # 4) 确保包含文件名里的 primary（组长）；去重
    if primary_id and not any(sid == primary_id for sid, _ in pairs):
        pairs.insert(0, (primary_id, primary_name))
    return pairs if pairs else [(primary_id, primary_name)]


class SubmissionProcessor:
    """提交处理器"""

    # 文件命名模式
    FILENAME_PATTERN = re.compile(
        r'(.+)-(\d{11})-([一-龥]{2,4})-实验报告'
    )

    # 源文件扩展名
    SOURCE_EXTENSIONS = {'.c', '.cpp', '.cc', '.cxx'}
    HEADER_EXTENSIONS = {'.h', '.hpp', '.hh', '.hxx'}

    def __init__(self, base_dir: Path):
        """
        初始化处理器

        Args:
            base_dir: 基础目录（例如：data/teaching/2026-春季/）
        """
        self.base_dir = Path(base_dir)

    def process_class_submissions(
        self,
        class_name: str,
        experiment_id: str,
        expand_team: bool = False,
    ) -> List[ProcessedSubmission]:
        """
        处理整个班级的提交

        Args:
            class_name: 班级名称
            experiment_id: 实验ID
            expand_team: 是否按"团队成员表"展开为每位成员一条提交（批阅用 True）。
                查重必须保持 False（避免同一小组报告被比对两次造成虚假相似）。
                展开时各成员共享同一报告/源码/代码块，仅学号、姓名不同。

        Returns:
            已处理提交列表
        """
        class_dir = self.base_dir / class_name / experiment_id
        reports_dir = class_dir / "reports"
        source_dir = class_dir / "source"

        if not reports_dir.exists():
            print(f"警告: 报告目录不存在: {reports_dir}")
            return []

        submissions = []

        # 遍历报告文件
        for report_file in reports_dir.glob("*-实验报告.*"):
            # 从文件名提取学生信息
            info = self._parse_filename(report_file.stem)
            if not info:
                print(f"警告: 无法解析文件名: {report_file.name}")
                continue

            class_name_parsed, student_id, name = info

            # 查找对应的源代码目录
            source_path = None
            project_info = None
            source_state = None

            if source_dir.exists():
                source_name = f"{class_name_parsed}-{student_id}-{name}-源代码"
                student_source = source_dir / source_name
                err_marker = source_dir / f"{source_name}.extraction_error"
                extraction_error = None
                if err_marker.exists():
                    try:
                        extraction_error = err_marker.read_text(encoding='utf-8')
                    except Exception:
                        extraction_error = None

                if student_source.exists():
                    source_path = student_source
                    project_info = self._analyze_project(student_source)
                # 无论目录是否存在，都做一次状态分类（携带 extraction_error），
                # 让格式问题（损坏/嵌套/空/未提交/纯Keil）在学生反馈中给出具体原因与改进方法。
                source_state = SourceStateClassifier.classify(source_path, extraction_error)

            # 读取报告内容
            report_text = self._read_report(report_file)

            # 提取代码块
            code_blocks = self._extract_code_blocks(report_text)

            # 成员列表：批阅时按团队表展开为每位成员一条；查重时仅组长（文件名）一人
            if expand_team:
                members = parse_team_members(report_text, student_id, name)
            else:
                members = [(student_id, name)]

            for sid, mname in members:
                submission = ProcessedSubmission(
                    student_id=sid,
                    name=mname,
                    class_name=class_name_parsed,
                    report_path=report_file,
                    report_text=report_text,
                    source_path=source_path,
                    project_info=project_info,
                    source_state=source_state,
                    code_blocks=code_blocks
                )

                submissions.append(submission)

        return submissions

    def process_single_submission(
        self,
        report_path: Path,
        source_path: Optional[Path] = None
    ) -> Optional[ProcessedSubmission]:
        """
        处理单个提交

        Args:
            report_path: 报告文件路径
            source_path: 源代码目录路径（可选）

        Returns:
            已处理提交，如果解析失败则返回None
        """
        # 从文件名提取学生信息
        info = self._parse_filename(report_path.stem)
        if not info:
            return None

        class_name, student_id, name = info

        # 读取报告内容
        report_text = self._read_report(report_path)

        # 分析源代码
        project_info = None
        source_state = None
        if source_path and source_path.exists():
            project_info = self._analyze_project(source_path)
        source_state = SourceStateClassifier.classify(source_path if (source_path and source_path.exists()) else None)

        # 提取代码块
        code_blocks = self._extract_code_blocks(report_text)

        return ProcessedSubmission(
            student_id=student_id,
            name=name,
            class_name=class_name,
            report_path=report_path,
            report_text=report_text,
            source_path=source_path,
            project_info=project_info,
            source_state=source_state,
            code_blocks=code_blocks
        )

    def _parse_filename(self, filename: str) -> Optional[Tuple[str, str, str]]:
        """
        解析文件名，提取学生信息

        Args:
            filename: 文件名（不含扩展名）

        Returns:
            (班级, 学号, 姓名) 或 None
        """
        match = self.FILENAME_PATTERN.search(filename)
        if match:
            return match.groups()
        return None

    def _read_report(self, report_path: Path) -> str:
        """
        读取报告内容

        Args:
            report_path: 报告文件路径

        Returns:
            报告文本内容
        """
        try:
            if report_path.suffix.lower() == '.pdf':
                # PDF文件需要特殊处理
                return f"[PDF文件: {report_path.name}]"
            else:
                # 读取docx文件并提取文本
                with open(report_path, 'rb') as f:
                    docx_data = f.read()
                xml_content = safe_extract_text_from_docx(docx_data)
                if xml_content:
                    # 解析XML内容提取文本
                    text = extract_text_from_docx_xml(xml_content)
                    return text if text else ""
                return ""
        except Exception as e:
            print(f"警告: 读取报告失败 {report_path.name}: {str(e)}")
            return ""

    def _extract_code_blocks(self, text: str) -> List[str]:
        """
        从文本中提取代码块

        Args:
            text: 文本内容

        Returns:
            代码块列表
        """
        code_blocks = []

        # Markdown代码块
        md_pattern = re.compile(r'```(?:c|cpp)?[^\n]*\n(.*?)```', re.DOTALL)
        code_blocks.extend(md_pattern.findall(text))

        # 如果没有找到Markdown代码块，尝试查找可能的代码片段
        if not code_blocks:
            # 查找包含函数定义的段落
            lines = text.split('\n')
            current_block = []
            in_code = False

            for line in lines:
                # 检测可能的代码行
                if re.search(r'(int|void|char|static)\s+\w+\s*\(', line):
                    in_code = True
                    current_block.append(line)
                elif in_code:
                    if line.strip() and not line.startswith(('   ', '\t')) and not re.search(r'[{};]', line):
                        # 可能是代码块结束
                        if current_block:
                            code_blocks.append('\n'.join(current_block))
                            current_block = []
                        in_code = False
                    else:
                        current_block.append(line)

            if current_block:
                code_blocks.append('\n'.join(current_block))

        return code_blocks

    def _analyze_project(self, project_path: Path) -> ProjectInfo:
        """
        分析源代码项目

        Args:
            project_path: 项目根目录

        Returns:
            项目信息
        """
        # 检测项目类型
        project_type = "simple"
        has_makefile = (project_path / "Makefile").exists()
        has_uvprojx = any(project_path.rglob("*.uvprojx"))

        if (project_path / "Core").exists():
            project_type = "cubemx"
        elif has_uvprojx:
            project_type = "keil"

        # 查找源文件
        source_files = []
        header_files = []
        main_files = []

        for ext in self.SOURCE_EXTENSIONS:
            source_files.extend(project_path.rglob(f"*{ext}"))

        for ext in self.HEADER_EXTENSIONS:
            header_files.extend(project_path.rglob(f"*{ext}"))

        # 查找主程序文件
        main_patterns = ['main.c', 'main.cpp', 'main.cc', 'main_interrupt.c']
        for pattern in main_patterns:
            main_candidates = list(project_path.rglob(pattern))
            if main_candidates:
                main_files.extend(main_candidates)

        return ProjectInfo(
            project_path=project_path,
            project_type=project_type,
            main_files=main_files,
            header_files=header_files,
            source_files=source_files,
            has_makefile=has_makefile,
            has_uvprojx=has_uvprojx
        )

    def get_student_summary(self, submissions: List[ProcessedSubmission]) -> Dict:
        """
        获取学生提交摘要

        Args:
            submissions: 已处理提交列表

        Returns:
            摘要字典
        """
        total = len(submissions)
        with_report = sum(1 for s in submissions if s.report_text)
        with_source = sum(1 for s in submissions if s.source_path)

        project_types = {}
        for s in submissions:
            if s.project_info:
                pt = s.project_info.project_type
                project_types[pt] = project_types.get(pt, 0) + 1

        return {
            'total': total,
            'with_report': with_report,
            'with_source': with_source,
            'missing_source': total - with_source,
            'project_types': project_types
        }


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='提交处理器')
    parser.add_argument('class_name', type=str, help='班级名称')
    parser.add_argument('experiment_id', type=str, help='实验ID')
    parser.add_argument('--base-dir', type=Path, default='data/teaching/2026-春季/', help='基础目录')

    args = parser.parse_args()

    processor = SubmissionProcessor(args.base_dir)

    submissions = processor.process_class_submissions(
        args.class_name,
        args.experiment_id
    )

    print(f"处理完成！")
    print(f"总提交数: {len(submissions)}")

    if submissions:
        summary = processor.get_student_summary(submissions)
        print(f"包含报告: {summary['with_report']}")
        print(f"包含源代码: {summary['with_source']}")
        print(f"缺少源代码: {summary['missing_source']}")
        print(f"项目类型分布: {summary['project_types']}")


if __name__ == '__main__':
    main()
