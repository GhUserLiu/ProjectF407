"""
基于新评分标准的评估引擎
所有评分都基于实验报告内容
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent.parent
# 默认使用最新的实验目录，可通过命令行参数覆盖
EXPERIMENT_DIR = BASE_DIR / "assignments" / "2026-春季" / "汽服2302B班" / "07-car-gear"
PROCESSED_DIR = EXPERIMENT_DIR / "processed"
DATA_DIR = Path(__file__).parent.parent / "rubrics"

def calculate_grade(score, grading_scale):
    """Convert numeric score to letter grade"""
    for grade, range_data in grading_scale.items():
        if range_data['min'] <= score <= range_data['max']:
            return grade, range_data['label']
    return 'F', '不及格'

def evaluate_by_criteria(text, category):
    """Evaluate a category based on its criteria"""
    score = 0
    feedback = []

    for criterion in category['criteria']:
        points = criterion['points']
        keywords = criterion.get('keywords', [])

        # Check if keywords are present in text
        found = sum(1 for kw in keywords if kw in text)

        # More lenient scoring:
        # If any keyword is found, give at least 60% of points
        # If 60%+ keywords found, give full points
        if keywords:
            coverage = found / len(keywords)
            if coverage >= 0.6:
                earned_points = points  # Full points if 60%+ keywords found
            elif found >= 1:
                earned_points = int(points * 0.7)  # 70% points if at least 1 keyword found
            else:
                earned_points = 0  # No points if no keywords found

            score += earned_points

            if earned_points >= points:
                feedback.append(f"{criterion['description']}")
            elif earned_points >= points * 0.6:
                feedback.append(f"{criterion['description']}(-{points - earned_points}分)")
            elif earned_points > 0:
                feedback.append(f"{criterion['description']}(-{points - earned_points}分)")
            else:
                feedback.append(f"{criterion['description']}(-{points}分)")
        else:
            # No keywords specified, give full points
            score += points
            if criterion.get('note'):
                feedback.append(f"{criterion['description']}({criterion['note']})")
            else:
                feedback.append(f"{criterion['description']}")

    return min(score, category['points']), feedback

def evaluate_report(extracted_content, rubric, quality_info=None):
    """Evaluate a single student's report based on new rubric"""
    text = extracted_content.get('full_text', '')

    evaluation = {
        'student_id': extracted_content['student_id'],
        'name': extracted_content.get('name', ''),
        'scores': {},
        'feedback': {},
        'total_score': 0,
        'grade': None,
        'grade_label': None,
        'quality_info': quality_info or {}
    }

    # Handle missing submissions
    if extracted_content.get('missing'):
        evaluation['total_score'] = 0
        evaluation['grade'] = 'F'
        evaluation['grade_label'] = '不及格'
        evaluation['scores'] = {
            'team_collaboration': 0,
            'attitude': 0,
            'completion': 0,
            'code_quality': 0,
            'report_quality': 0
        }
        evaluation['feedback'] = {
            'overall': ['未提交实验报告']
        }
        return evaluation

    # Evaluate each category
    for category in rubric['categories']:
        cat_id = category['id']

        if category.get('manual_evaluation'):
            # Manual evaluation categories (like attitude)
            evaluation['scores'][cat_id] = category['criteria'][0]['points']  # Default full points
            evaluation['feedback'][cat_id] = [
                f"{category['criteria'][0]['description']}: {category['criteria'][0].get('note', '需教师手工评定')}"
            ]
        else:
            # Auto-evaluate based on criteria
            score, feedback = evaluate_by_criteria(text, category)
            evaluation['scores'][cat_id] = score
            evaluation['feedback'][cat_id] = feedback

        evaluation['total_score'] += evaluation['scores'][cat_id]

    # Apply quality adjustment if available
    if quality_info and quality_info.get('overall_quality', 100) < 60:
        quality_score = quality_info.get('overall_quality', 50)
        # Reduce score if quality is poor
        reduction = int((evaluation['total_score'] * (60 - quality_score)) / 200)
        if reduction > 0:
            evaluation['total_score'] -= reduction
            evaluation['feedback']['quality_adjustment'] = [
                f"质量评估调整: 因内容深度不足，总分减少{reduction}分"
            ]

    # Calculate grade
    grading_scale = rubric['grading_scale']
    grade, label = calculate_grade(evaluation['total_score'], grading_scale)
    evaluation['grade'] = grade
    evaluation['grade_label'] = label

    return evaluation

def main():
    print("Evaluating student reports (new rubric)...")

    # Load extracted content
    content_path = PROCESSED_DIR / "extracted_content.json"
    if not content_path.exists():
        print("Error: extracted_content.json not found. Run extract_content.py first.")
        return

    with open(content_path, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    # Load rubric
    rubric_path = DATA_DIR / "rubric.json"
    with open(rubric_path, 'r', encoding='utf-8') as f:
        rubric = json.load(f)

    # Try to load quality assessment
    quality_path = PROCESSED_DIR / "quality_assessment.json"
    quality_data = None
    if quality_path.exists():
        with open(quality_path, 'r', encoding='utf-8') as f:
            quality_data = json.load(f)
        print("Using quality assessment data...")

    # Evaluate each report
    evaluations = []
    quality_scores = quality_data.get('quality_scores', {}) if quality_data else {}

    for content in extracted_data:
        student_id = content['student_id']
        quality_info = quality_scores.get(student_id) if quality_scores else None
        eval_result = evaluate_report(content, rubric, quality_info)
        evaluations.append(eval_result)
        print(f"  {eval_result['student_id']}: {eval_result['total_score']}分 ({eval_result['grade_label']})")

    # Save evaluations
    output_path = PROCESSED_DIR / "evaluations.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(evaluations, f, ensure_ascii=False, indent=2)

    print(f"\nEvaluated {len(evaluations)} reports")
    print(f"Results saved to: {output_path}")

    # Print summary
    scores = [e['total_score'] for e in evaluations]
    print(f"\nSummary:")
    print(f"  Average score: {sum(scores)/len(scores):.1f}")
    print(f"  Highest score: {max(scores)}")
    print(f"  Lowest score: {min(scores)}")
    print(f"  Grade distribution:")
    grade_counts = {}
    for e in evaluations:
        grade_counts[e['grade_label']] = grade_counts.get(e['grade_label'], 0) + 1
    for grade, count in sorted(grade_counts.items()):
        print(f"    {grade}: {count}")

if __name__ == "__main__":
    main()
