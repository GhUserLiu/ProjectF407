"""
检查新格式作业文件的提交时间
"""
import os
import zipfile
import re
import shutil
from datetime import datetime

# 检查一个学生的提交信息
check_dir = "assignments/2026-春季/汽服2302B班/07-car-gear/submissions/temp_new_format/check_one"

if os.path.exists(check_dir):
    # 找到 .doc 和 .docx 文件
    doc_file = None
    docx_file = None
    for f in os.listdir(check_dir):
        if f.endswith('.doc') and not f.startswith('~'):
            doc_file = os.path.join(check_dir, f)
        elif f.endswith('.docx') and not f.startswith('~'):
            docx_file = os.path.join(check_dir, f)

    print("Files found:")
    if doc_file:
        print(f"  DOC: {os.path.basename(doc_file)}")
    if docx_file:
        print(f"  DOCX: {os.path.basename(docx_file)}")

    # 检查 docx 文件的修改时间
    if docx_file:
        mtime = os.path.getmtime(docx_file)
        print(f"\nDOCX file mtime: {datetime.fromtimestamp(mtime)}")

        # 尝试读取 docx 的元数据
        try:
            from docx import Document
            doc = Document(docx_file)
            core_props = doc.core_properties
            if hasattr(core_props, 'modified') and core_props.modified:
                print(f"Document modified: {core_props.modified}")
            if hasattr(core_props, 'created') and core_props.created:
                print(f"Document created: {core_props.created}")
        except Exception as e:
            print(f"Cannot read metadata: {e}")

    # 检查 doc 文件（提交记录）
    if doc_file:
        print(f"\nDOC file size: {os.path.getsize(doc_file)} bytes")

        # 尝试用多种方式读取
        # 方法1: 作为 ole 文件读取
        try:
            import olefile
            if olefile.isOleFile(doc_file):
                print("DOC format: OLE")
                ole = olefile.OleFileIO(doc_file)
                # 尝试读取 WordDocument 流
                if 'WordDocument' in ole.listdir():
                    print("Contains WordDocument stream")
        except ImportError:
            pass

        # 方法2: 搜索二进制文件中的文本
        with open(doc_file, 'rb') as f:
            content = f.read()

        # 搜索日期字符串（多种编码）
        encodings = ['utf-8', 'gbk', 'utf-16-le']
        for enc in encodings:
            try:
                decoded = content.decode(enc, errors='ignore')
                # 搜索提交时间信息
                if '提交' in decoded or '时间' in decoded or '2026' in decoded:
                    print(f"\nFound text in {enc} encoding:")
                    # 提取包含时间信息的行
                    lines = decoded.split('\n')
                    for line in lines:
                        if '提交' in line or '时间' in line or ('2026' in line and '06' in line):
                            print(f"  {line.strip()[:100]}")
                    break
            except:
                pass

    print("\n--- Checking other students ---")

    # 检查多个学生的提交时间
    parent_dir = os.path.dirname(check_dir)
    zip_files = [f for f in os.listdir(parent_dir) if f.endswith('.zip') and not f.startswith('~')]

    print(f"\nFound {len(zip_files)} student ZIP files")

    # 解压几个学生的文件来查看时间模式
    import tempfile
    import subprocess

    results = []
    for i, zip_file in enumerate(zip_files[:5]):
        # 提取学号
        match = re.match(r'(\d+)', zip_file)
        if match:
            student_id = match.group(1)
        else:
            continue

        # 解压到临时目录
        temp_dir = tempfile.mkdtemp()
        try:
            subprocess.run(['unzip', '-q', os.path.join(parent_dir, zip_file), '-d', temp_dir],
                         capture_output=True)

            # 找里面的 ZIP
            inner_zips = [f for f in os.listdir(temp_dir) if f.endswith('.zip')]
            if inner_zips:
                inner_zip = os.path.join(temp_dir, inner_zips[0])
                inner_temp = tempfile.mkdtemp()
                try:
                    subprocess.run(['unzip', '-q', inner_zip, '-d', inner_temp],
                                 capture_output=True)

                    # 查找 docx 文件
                    docx_files = [f for f in os.listdir(inner_temp) if f.endswith('.docx')]
                    if docx_files:
                        docx_path = os.path.join(inner_temp, docx_files[0])
                        mtime = os.path.getmtime(docx_path)
                        results.append((student_id, datetime.fromtimestamp(mtime)))

                    # 清理
                    shutil.rmtree(inner_temp)
                except:
                    pass

            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error processing {zip_file}: {e}")

    print("\nSubmission times:")
    for student_id, sub_time in sorted(results, key=lambda x: x[1]):
        print(f"  {student_id}: {sub_time}")

else:
    print("Directory not found")
