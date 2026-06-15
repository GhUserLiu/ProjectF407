#!/bin/bash
# 实验报告整合脚本 - 按小组整合心得体会
# 用法: 在 submissions 目录下运行此脚本

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROCESSED_DIR="$BASE_DIR/../07-car-gear/processed"
OUTPUT_DIR="$BASE_DIR/temp_processing/integrated_reports"
EXTRACTED_JSON="$PROCESSED_DIR/extracted_content.json"

echo "========================================="
echo "   实验报告整合脚本 - 按小组整合心得体会"
echo "========================================="
echo ""
echo "工作目录: $BASE_DIR"
echo "处理目录: $PROCESSED_DIR"
echo "输出目录: $OUTPUT_DIR"
echo ""

# 检查必要文件
if [ ! -f "$EXTRACTED_JSON" ]; then
    echo "错误: 找不到 extracted_content.json 文件"
    echo "路径: $EXTRACTED_JSON"
    exit 1
fi

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

# 使用Python解析JSON并提取小组信息
python3 << 'PYTHON_SCRIPT'
import json
import re
import os
import sys

# 文件路径
processed_dir = os.path.expanduser("~/Projects/Workspace/stm32f407/docs/teaching/2026-春季/汽服2302B班/07-car-gear/processed")
output_dir = os.path.expanduser("~/Projects/Workspace/stm32f407/docs/teaching/2026-春季/汽服2302B班/07-car-gear/submissions/temp_processing/integrated_reports")
json_file = os.path.join(processed_dir, "extracted_content.json")

# 读取extracted_content.json
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"读取到 {len(data)} 个学生记录")

# 存储小组信息
groups = {}
ungrouped = []

# 解析每个学生的信息
for student in data:
    student_id = student.get('student_id', '')
    name = student.get('name', '')
    full_text = student.get('full_text', '')

    # 提取小组编号
    group_match = re.search(r'第([一二三四五六七八九十0-9]+)组', full_text)
    if group_match:
        group_num = group_match.group(1)
        # 转换中文数字
        cn_num = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
        if group_num in cn_num:
            group_num = cn_num[group_num]
        group_key = f"第{group_num}组"
    else:
        # 尝试其他模式
        group_match = re.search(r'(\d+)\s*组', full_text)
        if group_match:
            group_key = f"第{group_match.group(1)}组"
        else:
            # 尝试从团队成员信息中推断
            team_members = re.findall(r'(?:组长|组员|成员)[：:：\s]*([^\n]+)', full_text)
            # 暂时放到未分组
            group_key = None

    # 提取心得体会
    exp_match = re.search(r'个人心得体会[：:：\s\（\(]*.*?[\）\)]*\s*([\s\S]+?)(?=思考题|七、|附录|$)', full_text)
    if exp_match:
        experience = exp_match.group(1).strip()
    else:
        experience_match = re.search(r'6\.3\s*个人心得体会[：:：\s]*([\s\S]+?)(?=七、|思考题|$)', full_text)
        if experience_match:
            experience = experience_match.group(1).strip()
        else:
            experience = "未找到心得体会"

    # 提取小组成员姓名
    team_section = re.search(r'1\.1\s*团队成员基本信息[^\n]*[\s\S]*?1\.2\s*个人分工说明', full_text)
    if team_section:
        team_text = team_section.group(0)
        # 提取所有姓名（简单方法：找中文姓名模式）
        members = re.findall(r'([一-龥]{2,3})', team_text)
        members = list(set(members))  # 去重
        # 过滤掉常见的非姓名词汇
        exclude = {'组长', '组员', '成员', '姓名', '学号', '班级', '说明', '描述', '撰写', '负责', '完成', '编写', '设计', '实现', '调试', '接线', '测试', '记录', '整理', '汇总'}
        members = [m for m in members if m not in exclude and len(m) >= 2]
    else:
        members = []

    student_info = {
        'id': student_id,
        'name': name,
        'experience': experience,
        'members': members,
        'docx_path': student.get('docx_path', '')
    }

    if group_key:
        if group_key not in groups:
            groups[group_key] = []
        groups[group_key].append(student_info)
    else:
        ungrouped.append(student_info)

print(f"\n===== 小组统计 =====")
print(f"已分组: {sum(len(v) for v in groups.values())} 人")
print(f"未分组: {len(ungrouped)} 人")
print(f"\n===== 各小组详情 =====")

# 打印小组信息
for group_name in sorted(groups.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
    members = groups[group_name]
    print(f"\n{group_name}: {len(members)} 人")
    for m in members:
        print(f"  - {m['id']} {m['name']}")

if ungrouped:
    print(f"\n未分组: {len(ungrouped)} 人")
    for m in ungrouped:
        print(f"  - {m['id']} {m['name']}")

# 保存整合后的心得体会到文本文件
os.makedirs(output_dir, exist_ok=True)

print(f"\n===== 生成整合文件 =====")

for group_name, members in sorted(groups.items(), key=lambda x: int(re.search(r'\d+', x[0]).group())):
    if len(members) > 1:  # 只处理多人小组
        safe_name = group_name.replace('第', '').replace('组', '')
        output_file = os.path.join(output_dir, f'{group_name}_心得体会整合.txt')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"{group_name} - 心得体会整合\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"小组成员: {', '.join([m['name'] for m in members])}\n")
            f.write(f"学号列表: {', '.join([m['id'] for m in members])}\n\n")
            f.write("-" * 60 + "\n\n")

            for m in members:
                f.write(f"【{m['id']} - {m['name']}】\n")
                f.write(f"{m['experience']}\n")
                f.write("\n" + "=" * 60 + "\n\n")

        print(f"  ✓ 已生成: {os.path.basename(output_file)}")

print(f"\n整合文件已保存到: {output_dir")
PYTHON_SCRIPT

echo ""
echo "========================================="
echo "   整合完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 检查整合文件内容"
echo "2. 如需要，可以手动将内容复制到Word文档中"
echo "3. 打包为zip文件"
