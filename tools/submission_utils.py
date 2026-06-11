#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生提交内容提取工具（安全加固版）
Student Submission Extraction Utilities (Security Hardened)

从提交的ZIP文件中提取学生信息、小组编号和报告内容
安全加固：防御Zip炸弹、路径遍历、XXE注入攻击

作者: STM32F407 教学团队
版本: 2.0.0 - 安全增强版
"""

import zipfile
import io
import re
import logging
from pathlib import Path
from typing import Dict, Optional

# 导入安全工具模块
from tools.security.zip_validator import (
    ZipLimits, ZipValidationError,
    validate_path_traversal, validate_zip_size, safe_extract_inner_zip
)
from tools.security.xml_parser import safe_parse_xml_string, extract_text_from_docx_xml
from tools.security.path_validator import extract_safe_student_id

# 配置日志
logger = logging.getLogger(__name__)


def extract_text_from_docx(docx_data, limits=None):
    """
    从docx文件中提取文本（安全版本）

    Args:
        docx_data: docx文件二进制数据
        limits: ZIP限制配置（可选）

    Returns:
        提取的文本或None

    安全改进:
        - 使用安全XML解析器防御XXE攻击
        - 验证ZIP文件大小和结构
    """
    if limits is None:
        limits = ZipLimits()

    try:
        with zipfile.ZipFile(io.BytesIO(docx_data), 'r') as docx:
            # 验证docx ZIP结构（防御Zip炸弹）
            validate_zip_size(docx, limits)

            # 读取document.xml
            xml_content = docx.read('word/document.xml')

            # 使用安全XML解析器（防御XXE攻击）
            return extract_text_from_docx_xml(xml_content)

    except ZipValidationError as e:
        logger.warning(f"ZIP验证失败: {e}")
        return None
    except Exception as e:
        logger.error(f"提取docx文本失败: {e}")
        return None


def get_student_info(extract_dir, limits=None):
    """
    从答题记录和实验报告中提取学生信息（安全版本）

    Args:
        extract_dir: 提取后的提交目录
        limits: ZIP限制配置（可选）

    Returns:
        {学号: {'name': 姓名, 'time': 提交时间, 'content': 报告内容}}

    安全改进:
        - ZIP炸弹防护（文件大小、数量限制）
        - 路径遍历防护
        - 异常日志记录
    """
    if limits is None:
        limits = ZipLimits()

    student_info = {}

    for zip_file in extract_dir.glob('*.zip'):
        # 使用安全的学号提取函数
        student_id = extract_safe_student_id(zip_file.name)
        if not student_id:
            continue

        info = {'name': None, 'time': None, 'content': None}

        try:
            with zipfile.ZipFile(zip_file, 'r') as outer:
                # 验证外层ZIP（防御Zip炸弹）
                validate_zip_size(outer, limits)

                files = outer.namelist()
                if len(files) > 0 and files[0].endswith('.zip'):
                    # 安全提取内层ZIP
                    inner = safe_extract_inner_zip(outer, files[0], limits)
                    inner_files = inner.namelist()

                    # 从答题记录提取姓名和时间
                    doc_files = [f for f in inner_files if '答题记录' in f and f.endswith('.doc')]
                    if doc_files:
                        # 验证文件路径（防御路径遍历）
                        validate_path_traversal(doc_files[0])

                        doc_data = inner.read(doc_files[0])
                        doc_str = str(doc_data, errors='ignore')

                        pattern1 = r'<w:t>答题人：[^<]*</w:t>\s*.*?<w:t>([^<]+)</w:t>'
                        name_match = re.search(pattern1, doc_str, re.DOTALL)
                        if name_match:
                            info['name'] = name_match.group(1).strip()

                        pattern2 = r'<w:t>提交时间：[^<]*</w:t>\s*.*?<w:t>(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})[^<]*</w:t>'
                        time_match = re.search(pattern2, doc_str, re.DOTALL)
                        if time_match:
                            info['time'] = time_match.group(1).strip()

                    # 从实验报告提取内容
                    docx_files = [f for f in inner_files if f.endswith('.docx') and '答题记录' not in f]
                    if docx_files:
                        # 验证文件路径
                        validate_path_traversal(docx_files[0])

                        docx_data = inner.read(docx_files[0])
                        text = extract_text_from_docx(docx_data, limits)
                        if text:
                            content = re.sub(r'\s+', '', text)
                            info['content'] = content

                    if info['name'] or info['time']:
                        student_info[student_id] = info

        except ZipValidationError as e:
            logger.error(f"ZIP验证失败 ({student_id}): {e}")
        except Exception as e:
            logger.error(f"处理学生ZIP失败 ({student_id}): {e}")

    return student_info


def extract_team_number(text):
    """
    从文本中提取小组编号

    Args:
        text: 报告文本

    Returns:
        小组编号字符串或None
    """
    # 优先匹配更明确的格式
    patterns = [
        r'第(\d+)组',          # 第X组
        r'组号[：:\s]*(\d+)',  # 组号:X
        r'组长[：:\s]*[^\d]*(\d+)',  # 组长后的数字
        r'组员[：:\s]*[^\d]{0,50}第?(\d+)组',  # 组员后跟第X组
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            team_num = match.group(1)
            # 排除学号（11位）
            if len(team_num) != 11:
                return team_num

    # 如果都没匹配到，尝试搜索"组"周围的数字
    team_matches = re.findall(r'[^\d](\d{1,2})组|[^\d](\d{1,2})组组长', text)
    if team_matches:
        for match in team_matches:
            num = match[0] if match[0] else match[1]
            if num and len(num) <= 2:
                return num

    return None


def get_student_teams(extract_dir, limits=None):
    """
    获取学生的实验小组编号（安全版本）

    Args:
        extract_dir: 提取后的提交目录
        limits: ZIP限制配置（可选）

    Returns:
        {学号: 小组编号}

    安全改进:
        - ZIP炸弹防护
        - 路径遍历防护
        - 异常日志记录
    """
    if limits is None:
        limits = ZipLimits()

    student_teams = {}

    for zip_file in extract_dir.glob('*.zip'):
        # 使用安全的学号提取函数
        student_id = extract_safe_student_id(zip_file.name)
        if not student_id:
            continue

        try:
            with zipfile.ZipFile(zip_file, 'r') as outer:
                # 验证外层ZIP
                validate_zip_size(outer, limits)

                files = outer.namelist()
                if len(files) > 0 and files[0].endswith('.zip'):
                    # 安全提取内层ZIP
                    inner = safe_extract_inner_zip(outer, files[0], limits)

                    docx_files = [f for f in inner.namelist() if f.endswith('.docx') and '答题记录' not in f]
                    if docx_files:
                        # 验证文件路径
                        validate_path_traversal(docx_files[0])

                        docx_data = inner.read(docx_files[0])
                        text = extract_text_from_docx(docx_data, limits)
                        if text:
                            team = extract_team_number(text)
                            if team:
                                student_teams[student_id] = team
        except ZipValidationError as e:
            logger.error(f"ZIP验证失败 ({student_id}): {e}")
        except Exception as e:
            logger.error(f"处理学生ZIP失败 ({student_id}): {e}")

    return student_teams
