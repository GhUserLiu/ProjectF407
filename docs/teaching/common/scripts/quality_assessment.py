"""
质量评估与抄袭检测模块
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
import hashlib

BASE_DIR = Path(__file__).parent.parent.parent.parent
# 默认使用最新的实验目录，可通过命令行参数覆盖
EXPERIMENT_DIR = BASE_DIR / "assignments" / "2026-春季" / "汽服2302B班" / "07-car-gear"
PROCESSED_DIR = EXPERIMENT_DIR / "processed"

def extract_code_blocks(text):
    """Extract code blocks from report text"""
    # Look for code sections - usually in specific formats
    code_patterns = [
        r'```.*?```',  # Markdown code blocks
        r'void\s+\w+\([^)]*\)\s*{[^}]*}',  # C functions
        r'#include\s*<[^>]+>',  # Include statements
        r'HAL_GPIO_\w+\([^)]+\)',  # HAL function calls
        r'GPIO_[A-Z_]+',  # GPIO constants
    ]

    code_blocks = []
    for pattern in code_patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.MULTILINE)
        code_blocks.extend(matches)

    return code_blocks

def extract_paragraphs(text):
    """Extract meaningful paragraphs for comparison"""
    # Split by common delimiters
    paragraphs = re.split(r'\n\n+|\n\s*\n', text)
    # Filter out short paragraphs and code
    meaningful = [p.strip() for p in paragraphs if len(p.strip()) > 30 and not p.strip().startswith('#')]
    return meaningful

def calculate_similarity(text1, text2):
    """Calculate similarity ratio between two texts"""
    return SequenceMatcher(None, text1, text2).ratio()

def extract_group_number(name):
    """Extract group number from student name"""
    if not name:
        return None
    # Match patterns: "第X组", "第X组-XXX", "第X组XXX", "X组"
    import re
    match = re.search(r'第?([一二三四五六七八九十1-9]\d*)\s*组', name)
    if match:
        # Convert Chinese numbers to Arabic
        chinese_nums = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5',
                       '六': '6', '七': '7', '八': '8', '九': '9', '十': '10'}
        group_str = match.group(1)
        if group_str in chinese_nums:
            group_str = chinese_nums[group_str]
        try:
            return int(group_str)
        except ValueError:
            return group_str
    return None


def detect_plagiarism(extracted_data):
    """Detect plagiarism among student reports"""
    print("Running plagiarism detection...")
    print("  Note: Same-group reports are allowed to be similar (except personal reflections)")

    # Filter out missing submissions
    submissions = [s for s in extracted_data if not s.get('missing')]

    # Extract group numbers
    for s in submissions:
        s['group'] = extract_group_number(s.get('name', ''))

    plagiarism_results = {}
    suspicious_pairs = []

    # Compare each pair of submissions
    for i, s1 in enumerate(submissions):
        s1_id = s1['student_id']
        s1_group = s1.get('group')
        s1_text = s1.get('full_text', '')
        s1_para = extract_paragraphs(s1_text)

        similarities = defaultdict(dict)

        for j, s2 in enumerate(submissions):
            if i >= j:
                continue

            s2_id = s2['student_id']
            s2_group = s2.get('group')
            s2_text = s2.get('full_text', '')

            # Skip if same group (same-group reports are allowed to be similar)
            # Also skip if either group is unknown (we can't be sure they're different groups)
            if s1_group is not None and s2_group is not None:
                if s1_group == s2_group:
                    continue  # Same group, skip
            else:
                # At least one group is unknown, mark for manual review but don't auto-flag
                pass

            # Overall text similarity
            overall_sim = calculate_similarity(s1_text[:3000], s2_text[:3000])

            # Code similarity
            s1_code = extract_code_blocks(s1_text)
            s2_code = extract_code_blocks(s2_text)
            code_sim = 0
            if s1_code and s2_code:
                s1_code_str = ' '.join(s1_code)
                s2_code_str = ' '.join(s2_code)
                code_sim = calculate_similarity(s1_code_str, s2_code_str)

            # Paragraph similarity (check for identical paragraphs)
            s2_para = extract_paragraphs(s2_text)
            para_matches = 0
            for p1 in s1_para:
                for p2 in s2_para:
                    if calculate_similarity(p1, p2) > 0.85:
                        para_matches += 1
                        break

            # Calculate weighted similarity score
            weighted_sim = (overall_sim * 0.4 + code_sim * 0.4 +
                          (para_matches / max(len(s1_para), 1)) * 0.2)

            if weighted_sim > 0.5 or overall_sim > 0.7 or code_sim > 0.8:
                similarities[s2_id] = {
                    'overall': round(overall_sim * 100, 1),
                    'code': round(code_sim * 100, 1),
                    'paragraphs': para_matches,
                    'weighted': round(weighted_sim * 100, 1)
                }

                if weighted_sim > 0.6:
                    suspicious_pairs.append({
                        's1': s1_id,
                        's2': s2_id,
                        's1_name': s1.get('name', ''),
                        's2_name': s2.get('name', ''),
                        'similarity': round(weighted_sim * 100, 1)
                    })

        if similarities:
            plagiarism_results[s1_id] = dict(similarities)

    # Print summary
    print(f"  Found {len(suspicious_pairs)} suspicious pairs (>60% similarity)")

    return {
        'plagiarism_results': plagiarism_results,
        'suspicious_pairs': suspicious_pairs
    }

def assess_quality(extracted_data):
    """Assess quality of each report beyond keyword detection"""
    print("Running quality assessment...")

    quality_scores = {}

    for item in extracted_data:
        if item.get('missing'):
            quality_scores[item['student_id']] = {
                'overall_quality': 0,
                'content_depth': 0,
                'writing_quality': 0,
                'technical_accuracy': 0,
                'completeness': 0,
                'issues': ['未提交报告']
            }
            continue

        student_id = item['student_id']
        text = item.get('full_text', '')
        word_count = item.get('word_count', 0)

        quality = {
            'overall_quality': 0,
            'content_depth': 0,
            'writing_quality': 0,
            'technical_accuracy': 0,
            'completeness': 0,
            'issues': [],
            'strengths': []
        }

        # 1. Content Depth Analysis (0-20)
        depth_score = 0
        # Check for explanations, not just mentions
        if re.search(r'原理[是为因].{10,}', text):  # Has explanation of principles
            depth_score += 5
        if re.search(r'实现.{20,}', text):  # Has implementation details
            depth_score += 5
        if re.search(r'问题.{20,}(解决|处理)', text):  # Has problem-solving discussion
            depth_score += 5
        if re.search(r'(心得|体会|收获).{15,}', text):  # Has thoughtful reflection
            depth_score += 5
        quality['content_depth'] = depth_score

        # 2. Writing Quality (0-15)
        writing_score = 10  # Base score
        # Check for proper structure
        section_count = len(re.findall(r'[一二三四五六七八]、\s*\w+', text))
        if section_count >= 5:
            writing_score += 3
        elif section_count >= 3:
            writing_score += 1

        # Check for code formatting
        if '```' in text or '```' in text:
            writing_score += 2

        quality['writing_quality'] = min(writing_score, 15)

        # 3. Technical Accuracy (0-25)
        tech_score = 0
        technical_checks = [
            (r'PE4.*下降沿', 'PE4下降沿触发', 5),
            (r'PF9.*PF10', 'LED引脚配置', 5),
            (r'P.*R.*N.*D', '状态机逻辑', 5),
            (r'DWT.*消抖', 'DWT消抖实现', 5),
            (r'(HAL_|EXTI|NVIC)', 'HAL/中断使用', 5),
        ]
        for pattern, name, points in technical_checks:
            if re.search(pattern, text):
                tech_score += points
                quality['strengths'].append(f"技术要点正确:{name}")

        quality['technical_accuracy'] = tech_score

        # 4. Completeness (0-20)
        complete_score = 0
        required_elements = [
            (r'实验目的', '实验目的', 3),
            (r'硬件.*连接|接线', '硬件连接', 4),
            (r'软件.*设计|程序', '软件设计', 4),
            (r'测试|结果|现象', '测试结果', 4),
            (r'问题.*讨论', '问题讨论', 3),
            (r'代码|程序', '代码展示', 3),
        ]
        for pattern, name, points in required_elements:
            if re.search(pattern, text):
                complete_score += points
            else:
                quality['issues'].append(f'缺少完整{name}')

        quality['completeness'] = complete_score

        # 5. Overall Quality Calculation (normalized to 0-100)
        # Max possible scores: depth(20) + writing(15) + tech(25) + complete(21) = 81
        max_possible = 81
        quality['overall_quality'] = round(
            (quality['content_depth'] + quality['writing_quality'] +
             quality['technical_accuracy'] + quality['completeness']) / max_possible * 100, 1
        )

        # Quality grade
        if quality['overall_quality'] >= 85:
            quality['quality_grade'] = '优秀'
        elif quality['overall_quality'] >= 70:
            quality['quality_grade'] = '良好'
        elif quality['overall_quality'] >= 60:
            quality['quality_grade'] = '及格'
        else:
            quality['quality_grade'] = '需改进'

        quality_scores[student_id] = quality

    print(f"  Assessed quality for {len(quality_scores)} reports")

    return quality_scores

def generate_personalized_suggestions(evaluations, quality_scores, plagiarism_data):
    """Generate personalized suggestions for each student"""
    print("Generating personalized suggestions...")

    suggestions = {}

    for eval in evaluations:
        student_id = eval['student_id']
        grade = eval['grade']

        student_suggestions = {
            'student_id': student_id,
            'suggestions': [],
            'warnings': [],
            'plagiarism_warning': False
        }

        # Check for plagiarism
        plagiarism_results = plagiarism_data.get('plagiarism_results', {})
        if student_id in plagiarism_results:
            similar_students = plagiarism_results[student_id]
            if any(sim['weighted'] > 70 for sim in similar_students.values()):
                student_suggestions['plagiarism_warning'] = True
                student_suggestions['warnings'].append("⚠️ 报告内容与其他同学高度相似，请确认是否为原创")

        # Get quality score
        quality = quality_scores.get(student_id, {})

        # Generate suggestions based on weak areas
        scores = eval['scores']

        # Team collaboration suggestions
        if scores['team_collaboration'] < 12:
            student_suggestions['suggestions'].append("团队协作：请更详细地记录个人分工和协作过程")

        # Completion suggestions
        if scores['completion'] < 25:
            if quality.get('technical_accuracy', 0) < 15:
                student_suggestions['suggestions'].append("实验完成度：技术实现部分需要加强，建议参考示例代码")
            if quality.get('completeness', 0) < 12:
                student_suggestions['suggestions'].append("实验完成度：请补充完整的功能测试和验证")

        # Code quality suggestions
        if scores['code_quality'] < 15:
            student_suggestions['suggestions'].append("代码质量：增加代码注释，说明关键算法逻辑")

        # Report quality suggestions
        if scores['report_quality'] < 15:
            if quality.get('content_depth', 0) < 10:
                student_suggestions['suggestions'].append("报告质量：增加对原理和实现的深度分析")
            if quality.get('writing_quality', 0) < 10:
                student_suggestions['suggestions'].append("报告质量：注意排版格式，代码块需要清晰标注")
            if quality.get('completeness', 0) < 12:
                student_suggestions['suggestions'].append("报告质量：补充缺少的章节内容")

        # Quality-based suggestions
        overall_quality = quality.get('overall_quality', 0)
        if overall_quality < 60:
            student_suggestions['suggestions'].append("整体建议：报告内容需要大幅完善，建议参考优秀同学的结构")
        elif overall_quality >= 85:
            student_suggestions['suggestions'].append("整体表现优秀！继续保持")

        suggestions[student_id] = student_suggestions

    print(f"  Generated suggestions for {len(suggestions)} students")

    return suggestions

def main():
    """Run quality assessment and plagiarism detection"""
    print("=" * 60)
    print("质量评估与抄袭检测")
    print("=" * 60)

    # Load extracted content
    content_path = PROCESSED_DIR / "extracted_content.json"
    with open(content_path, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    # Load evaluations
    eval_path = PROCESSED_DIR / "evaluations.json"
    with open(eval_path, 'r', encoding='utf-8') as f:
        evaluations = json.load(f)

    # Run plagiarism detection
    plagiarism_data = detect_plagiarism(extracted_data)

    # Run quality assessment
    quality_scores = assess_quality(extracted_data)

    # Generate personalized suggestions
    suggestions = generate_personalized_suggestions(evaluations, quality_scores, plagiarism_data)

    # Save results
    output = {
        'plagiarism_data': plagiarism_data,
        'quality_scores': quality_scores,
        'suggestions': suggestions
    }

    output_path = PROCESSED_DIR / "quality_assessment.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")

    # Print summary
    print("\n--- Summary ---")
    print(f"Suspicious pairs (>60% similarity): {len(plagiarism_data['suspicious_pairs'])}")
    if plagiarism_data['suspicious_pairs']:
        print("\nTop suspicious pairs:")
        for pair in sorted(plagiarism_data['suspicious_pairs'],
                          key=lambda x: x['similarity'], reverse=True)[:5]:
            print(f"  {pair['s1']} & {pair['s2']}: {pair['similarity']}% similarity")

    quality_grades = defaultdict(int)
    for q in quality_scores.values():
        quality_grades[q.get('quality_grade', 'Unknown')] += 1
    print(f"\nQuality distribution:")
    for grade, count in sorted(quality_grades.items()):
        print(f"  {grade}: {count}")

if __name__ == "__main__":
    main()
