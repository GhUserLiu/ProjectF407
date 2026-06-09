#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取所有学生的提交时间并判断抄袭情况
"""

import os
import re
import zipfile
from datetime import datetime
from collections import defaultdict

def extract_text_from_wordml(doc_content):
    """从WordML格式中提取文本"""
    text_match = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', doc_content)
    return ''.join(text_match)

def extract_submission_time(text):
    """从文本中提取提交时间"""
    # 匹配格式: 提交时间：2026-06-07 01:05:53
    time_match = re.search(r'提交时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', text)
    if time_match:
        return time_match.group(1)
    return None

def parse_student_id(zip_name):
    """从zip文件名中提取学号"""
    # 格式: 23071140201-xxx-354113322.zip
    match = re.match(r'(\d{11})', zip_name)
    if match:
        return match.group(1)
    return None

def get_student_name(text):
    """从文本中提取学生姓名"""
    # 尝试从文件内容或文件名中提取
    name_match = re.search(r'姓名[：:]\s*([^\s\n]+)', text)
    if name_match:
        return name_match.group(1)
    return "未知"

def process_all_submissions(base_path="extracted_submissions"):
    """处理所有学生提交"""
    results = []

    # 遍历所有zip文件
    for zip_file in os.listdir(base_path):
        if not zip_file.endswith('.zip'):
            continue

        student_id = parse_student_id(zip_file)
        if not student_id:
            continue

        # 外层zip路径
        outer_zip_path = os.path.join(base_path, zip_file)

        try:
            # 读取外层zip
            with zipfile.ZipFile(outer_zip_path, 'r') as outer_zip:
                # 找到内层zip
                inner_files = [f for f in outer_zip.namelist() if f.endswith('.zip')]

                if not inner_files:
                    print(f"Warning: No inner zip found for {zip_file}")
                    continue

                # 读取内层zip
                inner_zip_data = outer_zip.read(inner_files[0])

                with zipfile.ZipFile(io.BytesIO(inner_zip_data), 'r') as inner_zip:
                    # 找到提交记录文件 (通常是包含"提交记录"的.doc文件)
                    doc_files = [f for f in inner_zip.namelist() if f.endswith('.doc') and '提交记录' in f]

                    if not doc_files:
                        # 如果找不到，尝试所有.doc文件
                        doc_files = [f for f in inner_zip.namelist() if f.endswith('.doc')]

                    if not doc_files:
                        print(f"Warning: No doc file found for {zip_file}")
                        continue

                    # 读取doc文件
                    doc_content = inner_zip.read(doc_files[0]).decode('utf-8-sig')
                    text = extract_text_from_wordml(doc_content)

                    submission_time = extract_submission_time(time)
                    if not submission_time:
                        print(f"Warning: No submission time found for {zip_file}")
                        # 尝试从文件名中获取时间戳
                        continue

                    student_name = get_student_name(text)

                    results.append({
                        'student_id': student_id,
                        'name': student_name,
                        'submission_time': submission_time,
                        'zip_file': zip_file
                    })

        except Exception as e:
            print(f"Error processing {zip_file}: {e}")
            continue

    return results

import io

def main():
    base_path = "extracted_submissions"

    print("开始提取学生提交时间...")
    results = process_all_submissions(base_path)

    # 按提交时间排序
    results.sort(key=lambda x: x['submission_time'])

    print(f"\n共找到 {len(results)} 个学生的提交记录\n")
    print("=" * 80)
    print(f"{'学号':<12} {'提交时间':<20} {'ZIP文件名'}")
    print("=" * 80)

    for r in results:
        print(f"{r['student_id']:<12} {r['submission_time']:<20} {r['zip_file'][:50]}")

    print("\n" + "=" * 80)
    print("说明：提交时间较早的学生可能是原创者，提交时间较晚的可能是抄袭者")

    # 保存结果到文件
    with open('submission_times.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"{'学号':<12} {'提交时间':<20} {'ZIP文件名'}\n")
        f.write("=" * 80 + "\n")
        for r in results:
            f.write(f"{r['student_id']:<12} {r['submission_time']:<20} {r['zip_file']}\n")

    print("\n结果已保存到 submission_times.txt")

if __name__ == "__main__":
    main()
