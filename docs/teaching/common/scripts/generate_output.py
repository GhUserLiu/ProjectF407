"""
生成输出文件：
1. 教师用Excel工作簿
2. 学生用反馈文档
"""

import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE_DIR = Path(__file__).parent.parent.parent.parent
# 默认使用最新的实验目录，可通过命令行参数覆盖
EXPERIMENT_DIR = BASE_DIR / "assignments" / "2026-春季" / "汽服2302B班" / "07-car-gear"
PROCESSED_DIR = EXPERIMENT_DIR / "processed"
DATA_DIR = Path(__file__).parent.parent / "rubrics"
OUTPUT_DIR = EXPERIMENT_DIR
TEACHER_OUTPUT = OUTPUT_DIR / "results"
STUDENT_OUTPUT = OUTPUT_DIR / "feedback"

def create_teacher_excel(evaluations, rubric, quality_data=None):
    """Create Excel workbook for teacher"""
    print("Creating teacher Excel workbook...")

    wb = Workbook()

    # Header styles
    header_font = Font(bold=True, size=11)
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")
    warning_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # ============================================================
    # Sheet 1: 总评表（汇总所有实验，目前仅有一个实验）
    # ============================================================
    ws_overall = wb.active
    ws_overall.title = "总评表"

    overall_headers = ['学号', '姓名', '实验07-档位', '实验-未完成', '总分', '等级', '备注']
    ws_overall.append(overall_headers)

    for cell in ws_overall[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    for eval in evaluations:
        student_id = eval['student_id']
        total_score = eval.get('total_score', 0)
        note = []
        if total_score == 0:
            note.append('未提交')
        ws_overall.append([
            student_id,
            eval.get('name', ''),
            total_score,
            '',
            total_score,
            eval.get('grade_label', ''),
            '; '.join(note)
        ])

    for row in ws_overall.iter_rows(min_row=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="center")

    # Auto-adjust column widths for overall sheet
    overall_widths = [12, 12, 15, 15, 10, 10, 40]
    for i, width in enumerate(overall_widths, 1):
        ws_overall.column_dimensions[chr(64 + i)].width = width

    # ============================================================
    # Sheet 2: 单次实验评分（实验07-档位）
    # ============================================================
    ws1 = wb.create_sheet("单次实验评分")

    # Write headers (with quality assessment columns)
    headers = ['学号', '姓名', '团队协作(15)', '实验态度(10)', '完成度(35)',
               '代码质量(20)', '报告质量(20)', '质量评分', '总分', '等级', '抄袭警告', '备注(扣分)']
    ws1.append(headers)

    # Style header row
    for cell in ws1[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = border

    # Get quality scores and plagiarism data
    quality_scores = quality_data.get('quality_scores', {}) if quality_data else {}
    plagiarism_results = quality_data.get('plagiarism_data', {}).get('plagiarism_results', {}) if quality_data else {}
    suggestions = quality_data.get('suggestions', {}) if quality_data else {}

    # Write student data
    for eval in evaluations:
        student_id = eval['student_id']
        quality = quality_scores.get(student_id, {})
        suggestion = suggestions.get(student_id, {})

        # Check for plagiarism
        plagiarism_warning = ""
        if suggestion.get('plagiarism_warning'):
            plagiarism_similar = plagiarism_results.get(student_id, {})
            high_sim = [(sid, s['weighted']) for sid, s in plagiarism_similar.items() if s['weighted'] > 70]
            if high_sim:
                plagiarism_warning = f"⚠️ 与{', '.join([f'{sid}%相似' for sid, _ in high_sim[:2]])}"

        row = [
            student_id,
            eval.get('name', ''),
            eval['scores']['team_collaboration'],
            eval['scores']['attitude'],
            eval['scores']['completion'],
            eval['scores']['code_quality'],
            eval['scores']['report_quality'],
            f"{quality.get('overall_quality', 0):.0f}",
            eval['total_score'],
            eval['grade_label'],
            plagiarism_warning
        ]

        # Compile feedback notes (仅显示扣分/问题)
        deduction_notes = []

        # 检查各项得分是否满分，未满分则添加扣分说明
        max_scores = {
            'team_collaboration': 15,
            'attitude': 10,
            'completion': 35,
            'code_quality': 20,
            'report_quality': 20
        }

        for cat_id, max_score in max_scores.items():
            score = eval['scores'].get(cat_id, 0)
            if score < max_score:
                cat_names = {
                    'team_collaboration': '团队协作',
                    'attitude': '实验态度',
                    'completion': '完成度',
                    'code_quality': '代码质量',
                    'report_quality': '报告质量'
                }
                deduction = max_score - score
                deduction_notes.append(f"{cat_names[cat_id]}-{deduction}分")

        # 添加抄袭警告作为扣分
        if plagiarism_warning:
            deduction_notes.append(plagiarism_warning)

        row.append('; '.join(deduction_notes) if deduction_notes else '')

        ws1.append(row)

        # Style data cells
        for cell in ws1[ws1.max_row]:
            cell.border = border
            cell.alignment = Alignment(vertical="center")

        # Highlight plagiarism warnings
        if plagiarism_warning:
            ws1[f'K{ws1.max_row}'].fill = warning_fill

    # Auto-adjust column widths
    column_widths = [12, 12, 15, 15, 15, 15, 15, 10, 10, 10, 15, 50]
    for i, width in enumerate(column_widths, 1):
        ws1.column_dimensions[chr(64 + i)].width = width

    # 设置打印区域，将单次实验评分相关的所有表格放在同一页
    ws1.page_setup.printArea = f"$A$1:$L${ws1.max_row}"
    ws1.page_setup.fitToPage = True
    ws1.page_setup.fitToHeight = 0
    ws1.page_setup.fitToWidth = 1

    # ============================================================
    # Sheet 3: 详细评分
    # ============================================================
    ws2 = wb.create_sheet("详细评分")
    detail_headers = ['学号', '姓名', '评分项', '得分', '扣分说明']
    ws2.append(detail_headers)
    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    for eval in evaluations:
        student_id = eval['student_id']
        student_name = eval.get('name', '')
        for cat_id, score in eval['scores'].items():
            cat_info = next((c for c in rubric['categories'] if c['id'] == cat_id), None)
            cat_name = cat_info['name'] if cat_info else cat_id
            feedback = '; '.join(eval['feedback'].get(cat_id, []))
            ws2.append([student_id, student_name, cat_name, score, feedback])

    ws2.column_dimensions['A'].width = 12
    ws2.column_dimensions['B'].width = 12
    ws2.column_dimensions['C'].width = 15
    ws2.column_dimensions['D'].width = 10
    ws2.column_dimensions['E'].width = 60

    # ============================================================
    # Sheet 4: 统计分析
    # ============================================================
    ws3 = wb.create_sheet("统计分析")
    scores = [e['total_score'] for e in evaluations if e.get('total_score', 0) > 0]
    submitted_count = len(scores)
    missing_count = len(evaluations) - submitted_count

    ws3['A1'] = '统计项目'
    ws3['B1'] = '数值'
    ws3['A1'].font = header_font
    ws3['B1'].font = header_font

    stats = [
        ('班级总人数', len(evaluations)),
        ('提交报告', submitted_count),
        ('未提交', missing_count),
        ('平均分', round(sum(scores) / submitted_count, 2) if submitted_count > 0 else 0),
        ('最高分', max(scores) if submitted_count > 0 else 0),
        ('最低分', min(scores) if submitted_count > 0 else 0),
        ('及格率(>=60)', f"{sum(1 for s in scores if s >= 60) / submitted_count * 100:.1f}%" if submitted_count > 0 else "0%"),
        ('优秀率(>=90)', f"{sum(1 for s in scores if s >= 90) / submitted_count * 100:.1f}%" if submitted_count > 0 else "0%")
    ]

    for i, (label, value) in enumerate(stats, 2):
        ws3[f'A{i}'] = label
        ws3[f'B{i}'] = value

    ws3.column_dimensions['A'].width = 20
    ws3.column_dimensions['B'].width = 15

    # ============================================================
    # Sheet 5: 评估说明
    # ============================================================
    ws4 = wb.create_sheet("评估说明")

    title_font = Font(bold=True, size=14)
    ws4['A1'] = '自动评估说明'
    ws4['A1'].font = title_font

    notes = [
        "",
        "本评分表由系统自动生成，基于以下评估逻辑：",
        "",
        "1. 评估方法：关键词检测",
        "   - 系统检测报告中是否包含各个章节和关键技术关键词",
        "   - 存在关键词即给予相应分数，未完全评估内容质量",
        "",
        "2. 建议调整事项：",
        "   - 【团队协作分】：建议根据实际分工情况调整",
        "   - 【实验态度分】：需根据考勤记录核实后修正",
        "   - 【实验完成度】：建议对照实际演示/验收结果调整",
        "   - 【代码质量】：建议人工审阅代码后调整",
        "   - 【报告质量】：建议人工审阅报告质量后调整",
        "",
        "3. 使用建议：",
        "   - 自动评分仅作为参考基准",
        "   - 教师应人工审阅后确定最终分数",
        "   - 可直接在Excel中修改分数",
        "",
        "4. 未提交学生：",
        "   - 5名学生未提交报告，记0分",
        "   - 学号: 23071140205, 23071140209, 23071140229, 23071140234, 23071140235"
    ]

    for i, note in enumerate(notes, 1):
        ws4[f'A{i}'] = note

    ws4.column_dimensions['A'].width = 80

    # Save
    output_path = TEACHER_OUTPUT / "汽服2302B班_07_档位实验_评分表.xlsx"
    wb.save(output_path)
    print(f"  Saved: {output_path}")

def create_student_feedback(evaluations, rubric, quality_data=None):
    """Create feedback documents for students"""
    print("Creating student feedback documents...")

    # Get reference answers and common issues
    ref_answers = rubric.get('reference_answers', {})
    common_issues = rubric.get('common_issues', {})

    # Get personalized suggestions
    suggestions = quality_data.get('suggestions', {}) if quality_data else {}
    quality_scores = quality_data.get('quality_scores', {}) if quality_data else {}

    # Create feedback template (only for students who submitted)
    for eval in evaluations:
        # Skip missing submissions
        if eval.get('total_score', 0) == 0 and eval.get('feedback', {}).get('overall') == ['未提交实验报告']:
            print(f"  Skipping {eval['student_id']}: No report submitted")
            continue

        student_id = eval['student_id']
        student_suggestions = suggestions.get(student_id, {})
        quality = quality_scores.get(student_id, {})

        doc = Document()

        # Title
        title = doc.add_paragraph('实验报告反馈')
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.runs[0].font.size = Pt(18)
        title.runs[0].font.bold = True

        # Experiment info
        doc.add_paragraph(f"实验名称: {rubric['experiment_name']}")
        doc.add_paragraph(f"学号: {student_id}")

        # Plagiarism warning if applicable
        if student_suggestions.get('plagiarism_warning'):
            warning_para = doc.add_paragraph()
            warning_run = warning_para.add_run("⚠️ 抄袭警告: ")
            warning_run.font.color.rgb = RGBColor(255, 0, 0)
            warning_para.add_run("你的报告内容与其他同学高度相似，请确认是否为原创。")
            doc.add_paragraph()

        # Grade
        grade_para = doc.add_paragraph()
        grade_para.add_run("评价等级: ").font.size = Pt(14)
        grade_run = grade_para.add_run(f"{eval['grade_label']}")
        grade_run.font.size = Pt(16)
        grade_run.font.bold = True
        grade_run.font.color.rgb = RGBColor(0, 128, 0) if eval['grade'] in ['A', 'B', 'C'] else RGBColor(255, 0, 0)

        doc.add_paragraph()  # Blank line

        # Only show what needs improvement (not complete reference answers)
        improvement_areas = []

        # Get quality-based issues
        if quality.get('issues'):
            improvement_areas.extend(quality['issues'])

        # Get personalized suggestions
        if student_suggestions.get('suggestions'):
            improvement_areas.extend(student_suggestions['suggestions'])

        # Only add improvement section if there are actual issues
        if improvement_areas:
            doc.add_heading("需要改进的地方", level=2)
            for area in improvement_areas:
                doc.add_paragraph(f"• {area}")

            # Add specific technical guidance based on weak areas
            scores = eval['scores']
            technical_guidance = []

            if scores['completion'] < 25:
                technical_guidance.append("关键要点：确保GPIO配置(PE4下降沿、PF9/PF10 LED)和状态机逻辑(P→R→N→D)正确实现")

            if scores['code_quality'] < 15:
                technical_guidance.append("代码规范：增加关键代码注释，说明DWT消抖和中断回调原理")

            if scores['report_quality'] < 15:
                technical_guidance.append("报告要求：补充硬件接线图、软件流程图、测试结果记录")

            if technical_guidance:
                doc.add_paragraph("\n关键技术要点：")
                for guidance in technical_guidance[:2]:
                    doc.add_paragraph(f"• {guidance}")
        else:
            # For students with no issues, show positive feedback
            doc.add_heading("评价", level=2)
            doc.add_paragraph("你的实验报告质量很好，继续保持！")
            if quality.get('strengths'):
                doc.add_paragraph("亮点:")
                for strength in quality['strengths'][:3]:
                    doc.add_paragraph(f"  • {strength}", style='List Bullet')

        # Save document
        output_path = STUDENT_OUTPUT / f"{eval['student_id']}_反馈.docx"
        doc.save(output_path)

    print(f"  Created {len(evaluations)} feedback documents")

def main():
    print("Generating output files...")

    # Load evaluations
    eval_path = PROCESSED_DIR / "evaluations.json"
    if not eval_path.exists():
        print("Error: evaluations.json not found. Run evaluate.py first.")
        return

    with open(eval_path, 'r', encoding='utf-8') as f:
        evaluations = json.load(f)

    # Load rubric
    rubric_path = DATA_DIR / "rubric.json"
    with open(rubric_path, 'r', encoding='utf-8') as f:
        rubric = json.load(f)

    # Load quality assessment data if available
    quality_path = PROCESSED_DIR / "quality_assessment.json"
    quality_data = None
    if quality_path.exists():
        with open(quality_path, 'r', encoding='utf-8') as f:
            quality_data = json.load(f)
        print("Using quality assessment data...")

    # Generate outputs
    create_teacher_excel(evaluations, rubric, quality_data)
    create_student_feedback(evaluations, rubric, quality_data)

    print("\nOutput generation complete!")
    print(f"Teacher Excel: {TEACHER_OUTPUT}")
    print(f"Student Feedbacks: {STUDENT_OUTPUT}")

    # Print plagiarism summary if available
    if quality_data and quality_data.get('plagiarism_data', {}).get('suspicious_pairs'):
        suspicious = quality_data['plagiarism_data']['suspicious_pairs']
        print(f"\nWARNING: Found {len(suspicious)} suspicious report pairs (>60% similarity)")
        print("  These have been marked in the Excel file.")

if __name__ == "__main__":
    main()
