#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
作业提交格式整理器
Submission Organizer

处理班级提交的压缩包，将其整理为标准格式：
- 提取实验报告到 reports/ 目录
- 提取源代码到 source/ 目录
- 自动重命名文件和文件夹

输入格式：
  班级压缩包
  └── 学生压缩包
      ├── 实验报告.docx
      └── 源代码.zip

输出格式：
  reports/
  └── 班级-学号-姓名-实验报告.docx
  source/
  └── 班级-学号-姓名-源代码/
"""

import os
import re
import shutil
import zipfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from ..security.zip_validator import safe_extract_zip
from ..security.path_validator import PathValidator


@dataclass
class StudentInfo:
    """学生信息"""
    student_id: str      # 学号
    name: str            # 姓名
    class_name: str      # 班级


@dataclass
class OrganizationResult:
    """整理结果"""
    total_students: int = 0
    successful: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    details: List[Dict] = field(default_factory=list)


class SubmissionOrganizer:
    """作业提交格式整理器"""

    # 文件扩展名模式
    REPORT_EXTENSIONS = {'.docx', '.doc', '.wps'}
    SOURCE_EXTENSIONS = {'.zip'}

    # 学号模式（11位数字）
    STUDENT_ID_PATTERN = re.compile(r'(\d{11})')

    # 姓名模式（2-4个汉字）
    NAME_PATTERN = re.compile(r'([一-龥]{2,4})')

    def __init__(self, base_dir: Path):
        """
        初始化整理器

        Args:
            base_dir: 基础目录（例如：data/teaching/2026-春季/）
        """
        self.base_dir = Path(base_dir)
        self.path_validator = PathValidator()

    def process_class_submission(
        self,
        class_zip: Path,
        class_name: str,
        experiment_id: str
    ) -> OrganizationResult:
        """
        处理班级提交压缩包

        Args:
            class_zip: 班级压缩包路径
            class_name: 班级名称（例如：汽服2302B班）
            experiment_id: 实验ID（例如：07-car-gear）

        Returns:
            整理结果
        """
        result = OrganizationResult()

        # 创建输出目录
        output_dir = self.base_dir / class_name / experiment_id
        reports_dir = output_dir / "reports"
        source_dir = output_dir / "source"

        reports_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)

        # 创建临时目录
        temp_dir = output_dir / ".temp"
        temp_dir.mkdir(exist_ok=True)

        try:
            # 1. 解压班级压缩包
            class_temp_dir = temp_dir / "class"
            class_temp_dir.mkdir(exist_ok=True)

            print(f"解压班级压缩包: {class_zip.name}")
            safe_extract_zip(class_zip, class_temp_dir)

            # 2. 查找所有学生压缩包
            student_zips = self._find_student_zips(class_temp_dir)
            result.total_students = len(student_zips)
            print(f"找到 {len(student_zips)} 个学生提交")

            # 3. 处理每个学生提交
            for student_zip in student_zips:
                student_result = self._process_student_submission(
                    student_zip,
                    class_name,
                    reports_dir,
                    source_dir,
                    temp_dir
                )

                if student_result['success']:
                    result.successful += 1
                    result.details.append(student_result)
                else:
                    result.failed += 1
                    result.errors.append(f"{student_zip.name}: {student_result.get('error', 'Unknown error')}")

        except Exception as e:
            result.errors.append(f"处理班级压缩包时出错: {str(e)}")

        finally:
            # 清理临时目录
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

        return result

    def _find_student_zips(self, class_dir: Path) -> List[Path]:
        """查找所有学生压缩包"""
        zips = []
        for item in class_dir.rglob("*.zip"):
            # 排除嵌套的ZIP（可能是源代码压缩包）
            # 只处理直接位于班级目录下的ZIP
            if item.parent == class_dir or (
                item.parent.name.startswith("23") and  # 学号开头
                item.stat().st_size < 50 * 1024 * 1024  # 小于50MB（学生提交不会太大）
            ):
                zips.append(item)
        return zips

    def _process_student_submission(
        self,
        student_zip: Path,
        class_name: str,
        reports_dir: Path,
        source_dir: Path,
        temp_dir: Path
    ) -> Dict:
        """
        处理单个学生提交

        Args:
            student_zip: 学生压缩包路径
            class_name: 班级名称
            reports_dir: 报告输出目录
            source_dir: 源代码输出目录
            temp_dir: 临时目录

        Returns:
            处理结果字典
        """
        result = {
            'success': False,
            'student_id': None,
            'name': None,
            'report_path': None,
            'source_path': None,
            'error': None
        }

        try:
            # 1. 从文件名提取学生信息
            student_info = self._extract_student_info(student_zip, class_name)
            if not student_info:
                result['error'] = "无法从文件名提取学生信息"
                return result

            result['student_id'] = student_info.student_id
            result['name'] = student_info.name

            # 2. 创建学生临时目录
            student_temp = temp_dir / student_info.student_id
            student_temp.mkdir(exist_ok=True)

            # 3. 解压学生压缩包
            safe_extract_zip(student_zip, student_temp)

            # 4. 查找并处理报告文件
            report_file = self._find_report_file(student_temp)
            if report_file:
                # 重命名并移动到reports目录
                new_report_name = f"{class_name}-{student_info.student_id}-{student_info.name}-实验报告{report_file.suffix}"
                new_report_path = reports_dir / new_report_name
                shutil.move(str(report_file), str(new_report_path))
                result['report_path'] = str(new_report_path)
                print(f"  ✓ 处理报告: {new_report_name}")
            else:
                result['error'] = "未找到实验报告文件"
                return result

            # 5. 查找并处理源代码
            source_zip = self._find_source_zip(student_temp)
            if source_zip:
                # 创建源代码目录
                source_name = f"{class_name}-{student_info.student_id}-{student_info.name}-源代码"
                source_path = source_dir / source_name
                source_path.mkdir(exist_ok=True)

                # 解压源代码
                safe_extract_zip(source_zip, source_path)
                result['source_path'] = str(source_path)
                print(f"  ✓ 处理源代码: {source_name}")
            else:
                print(f"  ⚠ 未找到源代码压缩包: {student_zip.name}")

            result['success'] = True

        except Exception as e:
            result['error'] = str(e)

        return result

    def _extract_student_info(self, file_path: Path, class_name: str) -> Optional[StudentInfo]:
        """
        从文件名提取学生信息

        支持格式：
        - 23071140101-张三.zip
        - 学号-姓名.zip
        - 任意包含学号和姓名的格式

        Args:
            file_path: 文件路径
            class_name: 班级名称

        Returns:
            学生信息，如果提取失败则返回None
        """
        filename = file_path.stem  # 去除扩展名

        # 尝试提取学号
        student_id_match = self.STUDENT_ID_PATTERN.search(filename)
        if not student_id_match:
            return None

        student_id = student_id_match.group(1)

        # 尝试提取姓名
        name_match = self.NAME_PATTERN.search(filename)
        if not name_match:
            return None

        name = name_match.group(1)

        return StudentInfo(
            student_id=student_id,
            name=name,
            class_name=class_name
        )

    def _find_report_file(self, directory: Path) -> Optional[Path]:
        """查找报告文件"""
        for ext in self.REPORT_EXTENSIONS:
            # 查找直接匹配的文件
            for file in directory.glob(f"*{ext}"):
                return file

            # 递归查找
            for file in directory.rglob(f"*{ext}"):
                # 确保不是源代码目录中的文件
                if 'source' not in str(file).lower() and 'code' not in str(file).lower():
                    return file

        return None

    def _find_source_zip(self, directory: Path) -> Optional[Path]:
        """查找源代码压缩包"""
        # 查找可能的源代码压缩包
        patterns = ['*源代码*.zip', '*code*.zip', '*project*.zip', '*工程*.zip']

        for pattern in patterns:
            for file in directory.glob(pattern):
                return file

        # 如果没有找到，查找任意ZIP（排除可能的重复）
        zips = list(directory.glob("*.zip"))
        if len(zips) == 1:
            return zips[0]

        return None

    def generate_summary_report(self, result: OrganizationResult, output_path: Path):
        """生成整理报告"""
        lines = [
            "=" * 60,
            "作业提交格式整理报告",
            "=" * 60,
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "统计信息:",
            f"  总学生数: {result.total_students}",
            f"  成功处理: {result.successful}",
            f"  处理失败: {result.failed}",
            "",
        ]

        if result.details:
            lines.extend([
                "成功详情:",
            ])
            for detail in result.details:
                lines.append(
                    f"  {detail['student_id']}-{detail['name']}: "
                    f"报告={Path(detail['report_path']).name if detail['report_path'] else '无'}, "
                    f"源代码={Path(detail['source_path']).name if detail['source_path'] else '无'}"
                )

        if result.errors:
            lines.extend([
                "",
                "错误详情:",
            ])
            for error in result.errors:
                lines.append(f"  ❌ {error}")

        lines.append("=" * 60)

        report_text = "\n".join(lines)
        output_path.write_text(report_text, encoding='utf-8')

        # 同时生成JSON格式
        import json
        json_path = output_path.with_suffix('.json')
        json_data = {
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total': result.total_students,
                'successful': result.successful,
                'failed': result.failed
            },
            'details': result.details,
            'errors': result.errors
        }
        json_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description='作业提交格式整理器')
    parser.add_argument('class_zip', type=Path, help='班级压缩包路径')
    parser.add_argument('class_name', type=str, help='班级名称（例如：汽服2302B班）')
    parser.add_argument('experiment_id', type=str, help='实验ID（例如：07-car-gear）')
    parser.add_argument('--base-dir', type=Path, default='data/teaching/2026-春季/', help='基础目录')

    args = parser.parse_args()

    organizer = SubmissionOrganizer(args.base_dir)

    print(f"开始处理班级提交: {args.class_name}")
    print(f"实验: {args.experiment_id}")
    print(f"压缩包: {args.class_zip}")
    print()

    result = organizer.process_class_submission(
        args.class_zip,
        args.class_name,
        args.experiment_id
    )

    print()
    print("=" * 60)
    print("处理完成！")
    print(f"成功: {result.successful}/{result.total_students}")
    print(f"失败: {result.failed}/{result.total_students}")

    if result.errors:
        print()
        print("错误:")
        for error in result.errors:
            print(f"  {error}")

    # 生成报告
    output_dir = args.base_dir / args.class_name / args.experiment_id
    report_path = output_dir / "整理报告.txt"
    organizer.generate_summary_report(result, report_path)
    print(f"报告已生成: {report_path}")


if __name__ == '__main__':
    main()
