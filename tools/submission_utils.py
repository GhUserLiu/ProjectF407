#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
学生提交内容提取工具
Student Submission Extraction Utilities

从提交的ZIP文件中提取学生信息、小组编号和报告内容
"""

import zipfile
import io
import re
from pathlib import Path
from xml.etree import ElementTree as ET


def extract_text_from_docx(docx_data):
    """从docx文件中提取文本"""
    try:
        with zipfile.ZipFile(io.BytesIO(docx_data), 'r') as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            texts = []
            for elem in root.iter():
                if elem.tag.endswith('}t'):
                    if elem.text:
                        texts.append(elem.text)
            return ''.join(texts)
    except:
        return None


def get_student_info(extract_dir):
    """
    从答题记录和实验报告中提取学生信息

    Args:
        extract_dir: 提取后的提交目录

    Returns:
        {学号: {'name': 姓名, 'time': 提交时间, 'content': 报告内容}}
    """
    student_info = {}

    for zip_file in extract_dir.glob('*.zip'):
        match = re.search(r'(\d{11})', zip_file.name)
        if not match:
            continue
        student_id = match.group(1)

        info = {'name': None, 'time': None, 'content': None}

        try:
            with zipfile.ZipFile(zip_file, 'r') as outer:
                files = outer.namelist()
                if files[0].endswith('.zip'):
                    inner_data = outer.read(files[0])
                    with zipfile.ZipFile(io.BytesIO(inner_data), 'r') as inner:
                        inner_files = inner.namelist()

                        # 从答题记录提取姓名和时间
                        doc_files = [f for f in inner_files if '答题记录' in f and f.endswith('.doc')]
                        if doc_files:
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
                            docx_data = inner.read(docx_files[0])
                            text = extract_text_from_docx(docx_data)
                            if text:
                                # 清理文本：移除空白字符，用于相似度比较
                                content = re.sub(r'\s+', '', text)
                                info['content'] = content

                        if info['name'] or info['time']:
                            student_info[student_id] = info

        except Exception as e:
            pass

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


def get_student_teams(extract_dir):
    """
    获取学生的实验小组编号

    Args:
        extract_dir: 提取后的提交目录

    Returns:
        {学号: 小组编号}
    """
    student_teams = {}

    for zip_file in extract_dir.glob('*.zip'):
        match = re.search(r'(\d{11})', zip_file.name)
        if not match:
            continue
        student_id = match.group(1)

        try:
            with zipfile.ZipFile(zip_file, 'r') as outer:
                files = outer.namelist()
                if files[0].endswith('.zip'):
                    inner_data = outer.read(files[0])
                    with zipfile.ZipFile(io.BytesIO(inner_data), 'r') as inner:
                        docx_files = [f for f in inner.namelist() if f.endswith('.docx') and '答题记录' not in f]
                        if docx_files:
                            docx_data = inner.read(docx_files[0])
                            text = extract_text_from_docx(docx_data)
                            if text:
                                team = extract_team_number(text)
                                if team:
                                    student_teams[student_id] = team
        except:
            pass

    return student_teams
