#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增强版实验报告查重与质量评估系统
Enhanced Plagiarism Detection and Quality Assessment System for Lab Reports

功能：
1. 多算法文本相似度检测
2. 模板内容智能排除
3. 代码相似度专项检测
4. 基于 Rubric 的详细评分
5. 技术要点专项检查
6. 学生个性化反馈生成
7. 详细报告生成（Excel/JSON/HTML/Markdown）
8. 可视化相似度矩阵

作者: STM32F407 教学团队
版本: 2.1.0
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 导入自定义模块
from tools.plagiarism.core import (
    PlagiarismDetector,
    TextPreprocessor,
    SimilarityMethod,
    SimilarityResult
)
from tools.plagiarism.algorithms import (
    sequence_similarity,
    cosine_similarity,
    hybrid_similarity
)
from tools.plagiarism.template import (
    TemplateExtractor,
    TemplateFilter,
    load_template_from_file,
    create_filter_from_reports
)
from tools.plagiarism.report import (
    PlagiarismReport,
    SimilarityMatrix,
    ReportConfig
)
from tools.plagiarism.grading import (
    RubricLoader,
    RubricGrader,
    GradingResult,
    batch_grade,
    load_rubric_for_experiment
)
from tools.plagiarism.technical_checks import (
    TechnicalChecker,
    ExperimentType,
    ContentStructureChecker,
    CodeSnippetChecker,
    ThinkingQuestionsChecker
)
from tools.plagiarism.feedback import (
    FeedbackGenerator,
    HTMLFeedbackGenerator,
    save_student_feedback
)


class EnhancedPlagiarismSystem:
    """增强版查重系统"""

    def __init__(
        self,
        experiment_dir: Path,
        experiment_type: str = '档位实验',
        class_name: str = '未知班级',
        threshold: float = 60.0,
        method: SimilarityMethod = SimilarityMethod.HYBRID,
        use_template_filter: bool = True,
        template_path: Optional[Path] = None
    ):
        """
        初始化系统

        Args:
            experiment_dir: 实验目录
            experiment_type: 实验类型
            class_name: 班级名称
            threshold: 可疑阈值
            method: 相似度计算方法
            use_template_filter: 是否使用模板过滤
            template_path: 模板文件路径
        """
        self.experiment_dir = experiment_dir
        self.experiment_type = experiment_type
        self.class_name = class_name
        self.threshold = threshold
        self.method = method

        # 目录设置
        self.submissions_dir = experiment_dir / 'submissions' / 'extracted'
        self.output_dir = experiment_dir / 'results'
        self.output_dir.mkdir(exist_ok=True)

        # 模板过滤器
        self.template_filter = None
        if use_template_filter:
            self._init_template_filter(template_path)

        # 检测器和评估器
        self.detector = None
        self.assessor = None

        # 数据
        self.submissions: Dict[str, Dict] = {}
        self.group_info: Dict[str, str] = {}

        # 结果
        self.all_results: Dict[str, List[SimilarityResult]] = {}
        self.suspicious: List[SimilarityResult] = []
        self.groups: List[Dict] = []
        self.quality_results: List[AssessmentResult] = []

    def _init_template_filter(self, template_path: Optional[Path]):
        """初始化模板过滤器"""
        if template_path and template_path.exists():
            print(f"加载模板文件: {template_path}")
            self.template_filter = load_template_from_file(template_path)
        elif self.submissions_dir.exists():
            # 从报告中分析提取模板
            print("从报告中分析提取模板内容...")
            report_files = list(self.submissions_dir.glob('*.zip'))

            if report_files:
                self.template_filter = create_filter_from_reports(
                    report_files[:10],  # 分析前10份
                    min_occurrence=5,
                    threshold=0.4
                )
                print(f"  提取到 {len(self.template_filter.patterns)} 个模板模式")

    def load_submissions(self):
        """加载学生提交内容"""
        print("\n" + "="*60)
        print("加载学生提交内容")
        print("="*60)

        if not self.submissions_dir.exists():
            print(f"错误: 提交目录不存在: {self.submissions_dir}")
            return False

        # 使用提交内容提取工具
        from tools.submission_utils import get_student_info, get_student_teams

        # 提取学生信息
        student_info = get_student_info(self.submissions_dir)
        print(f"提取到 {len(student_info)} 个学生信息")

        # 提取小组信息
        self.group_info = get_student_teams(self.submissions_dir)
        print(f"提取到 {len(self.group_info)} 个学生的小组编号")

        # 转换为系统格式
        for student_id, info in student_info.items():
            if info.get('content'):
                # 应用模板过滤
                text = info['content']
                if self.template_filter:
                    original_len = len(text)
                    text = self.template_filter.filter_text(text)
                    filtered_ratio = 1 - len(text) / original_len if original_len > 0 else 0

                self.submissions[student_id] = {
                    'name': info.get('name', ''),
                    'text': text,
                    'group': self.group_info.get(student_id),
                    'raw_content': info.get('content')
                }

        print(f"成功加载 {len(self.submissions)} 份有效报告")
        return len(self.submissions) > 0

    def run_plagiarism_detection(self):
        """执行查重检测"""
        print("\n" + "="*60)
        print("执行查重检测")
        print("="*60)

        # 创建检测器
        self.detector = PlagiarismDetector(
            method=self.method,
            threshold=self.threshold,
            remove_template=self.template_filter is not None,
            group_info=self.group_info
        )

        # 执行检测
        self.all_results, self.suspicious = self.detector.detect(self.submissions)

        # 检测抄袭团伙
        self.groups = self.detector.detect_groups(self.suspicious)

        # 输出结果
        print(f"检测人数: {len(self.submissions)}")
        print(f"可疑对数: {len(self.suspicious)} (≥{self.threshold}%)")
        print(f"涉嫌抄袭人数: {len(self._get_suspicious_students())}")
        print(f"抄袭团伙数: {len(self.groups)}")

        if self.suspicious:
            print("\n最高相似度对:")
            top = sorted(self.suspicious, key=lambda x: x.overall_similarity, reverse=True)[:3]
            for r in top:
                metadata = r.metadata
                print(f"  {r.student_id} & {r.similar_to}: {r.overall_similarity:.1f}% "
                      f"({'跨组' if r.is_cross_group else '同组'})")

        return True

    def run_quality_assessment(self):
        """执行质量评估（基于 Rubric 评分）"""
        print("\n" + "="*60)
        print("执行详细评分与质量评估")
        print("="*60)

        # 加载评分标准
        rubric_path = Path(__file__).parent.parent / 'docs/teaching/common/rubrics/rubric.json'
        rubric = load_rubric_for_experiment(self.experiment_type)
        print(f"加载评分标准: {rubric.get('experiment_name', '默认')}")

        # 准备抄袭数据
        plagiarism_data = {}
        for sid, results in self.all_results.items():
            if results:
                plagiarism_data[sid] = [
                    {
                        'similar_to': r.similar_to,
                        'overall': r.overall_similarity,
                        'weighted': r.overall_similarity * 0.6 + r.code_similarity * 0.4
                    }
                    for r in results
                ]

        # 执行 Rubric 评分
        print("执行基于 Rubric 的详细评分...")
        self.grading_results = batch_grade(
            self.submissions,
            rubric,
            experiment_type=self.experiment_type
        )

        # 执行技术要点检查
        print("执行技术要点专项检查...")
        self.technical_results = {}

        # 确定实验类型
        exp_type = ExperimentType.CAR_GEAR if '档位' in self.experiment_type else ExperimentType.TURN_SIGNAL

        for student_id, submission in self.submissions.items():
            text = submission.get('text', '')
            if text:
                self.technical_results[student_id] = TechnicalChecker.check_all(text, exp_type)

        # 统计
        grades = {}
        for r in self.grading_results:
            grades[r.grade] = grades.get(r.grade, 0) + 1

        print(f"\n评分人数: {len(self.grading_results)}")
        print(f"等级分布:")
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grades.get(grade, 0)
            if count > 0:
                print(f"  {grade}: {count} 人")

        avg_score = sum(r.total_score for r in self.grading_results) / len(self.grading_results) if self.grading_results else 0
        print(f"平均分: {avg_score:.1f}")

        return True

    def generate_reports(self, formats: List[str] = None):
        """生成报告"""
        print("\n" + "="*60)
        print("生成查重报告")
        print("="*60)

        if formats is None:
            formats = ['excel', 'json', 'html']

        # 创建报告配置
        config = ReportConfig(
            output_dir=self.output_dir,
            experiment_name=f"{self.experiment_type}实验",
            class_name=self.class_name,
            threshold=self.threshold
        )

        # 创建报告生成器
        report_gen = PlagiarismReport(config)
        report_gen.add_results(self.all_results, self.suspicious)
        report_gen.add_groups(self.groups)

        # 生成各种格式
        output_paths = []

        if 'excel' in formats:
            path = report_gen.generate_excel('查重报告.xlsx')
            output_paths.append(path)
            print(f"Excel 报告: {path}")

        if 'json' in formats:
            path = report_gen.generate_json('查重报告.json')
            output_paths.append(path)
            print(f"JSON 报告: {path}")

        if 'html' in formats:
            path = report_gen.generate_html('查重报告.html')
            output_paths.append(path)
            print(f"HTML 报告: {path}")

        return output_paths

    def save_quality_results(self):
        """保存详细评分结果"""
        print("\n保存详细评分结果...")

        output = []

        # 合并 Rubric 评分和技术检查结果
        for grading_result in self.grading_results:
            student_id = grading_result.student_id

            # 获取技术检查结果
            tech_result = self.technical_results.get(student_id, (0, [], [], []))

            result_dict = {
                'student_id': student_id,
                'name': grading_result.name,
                'total_score': grading_result.total_score,
                'total_possible': grading_result.total_possible,
                'percentage': grading_result.percentage,
                'grade': grading_result.grade,
                'category_scores': {
                    cat_id: {
                        'name': score.name,
                        'earned': score.points_earned,
                        'possible': score.points_possible,
                        'percentage': score.percentage,
                        'feedback': score.feedback
                    }
                    for cat_id, score in grading_result.category_scores.items()
                },
                'technical_check': {
                    'score': tech_result[0],
                    'strengths': tech_result[2],
                    'weaknesses': tech_result[3]
                },
                'strengths': grading_result.strengths,
                'weaknesses': grading_result.weaknesses,
                'recommendations': grading_result.recommendations,
                'auto_confidence': grading_result.auto_confidence
            }

            # 添加抄袭风险
            if student_id in self.all_results and self.all_results[student_id]:
                max_sim = max(r.overall_similarity for r in self.all_results[student_id])
                result_dict['plagiarism_risk'] = max_sim / 100
            else:
                result_dict['plagiarism_risk'] = 0.0

            output.append(result_dict)

        output_path = self.output_dir / 'grading_results.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"详细评分结果: {output_path}")
        return output_path

    def generate_student_feedback(self, format: str = 'md'):
        """为学生生成个性化反馈文件"""
        print(f"\n生成学生反馈文件 ({format} 格式)...")

        feedback_dir = self.output_dir / 'feedback'
        feedback_dir.mkdir(exist_ok=True)

        generated = []

        for grading_result in self.grading_results:
            student_id = grading_result.student_id

            # 获取技术检查结果
            tech_result = self.technical_results.get(student_id, (0, [], [], []))

            # 获取抄袭风险
            plagiarism_risk = 0.0
            if student_id in self.all_results and self.all_results[student_id]:
                max_sim = max(r.overall_similarity for r in self.all_results[student_id])
                plagiarism_risk = max_sim / 100

            # 生成反馈文件
            try:
                feedback_path = save_student_feedback(
                    student_id,
                    grading_result.name,
                    grading_result,
                    tech_result,
                    feedback_dir,
                    plagiarism_risk,
                    format
                )
                generated.append(feedback_path)
            except Exception as e:
                print(f"  警告: {student_id} 反馈生成失败: {e}")

        print(f"生成 {len(generated)} 个反馈文件: {feedback_dir}")
        return generated

    def _get_suspicious_students(self) -> set:
        """获取所有涉嫌抄袭的学生"""
        students = set()
        for result in self.suspicious:
            students.add(result.student_id)
            students.add(result.similar_to)
        return students

    def run_full_analysis(self):
        """运行完整分析流程"""
        print("\n" + "="*60)
        print(f"增强版实验报告查重与评分系统 v2.1")
        print(f"实验类型: {self.experiment_type}")
        print(f"班级: {self.class_name}")
        print(f"查重阈值: {self.threshold}%")
        print(f"相似度算法: {self.method.value}")
        print("="*60)

        start_time = datetime.now()

        # 1. 加载提交内容
        if not self.load_submissions():
            print("错误: 无法加载提交内容")
            return False

        # 2. 执行查重检测
        if not self.run_plagiarism_detection():
            print("错误: 查重检测失败")
            return False

        # 3. 执行详细评分（基于 Rubric + 技术检查）
        if not self.run_quality_assessment():
            print("错误: 质量评估失败")
            return False

        # 4. 生成查重报告
        self.generate_reports(['excel', 'json', 'html'])

        # 5. 保存详细评分结果
        self.save_quality_results()

        # 6. 生成学生个性化反馈
        self.generate_student_feedback('md')
        self.generate_student_feedback('html')

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "="*60)
        print(f"✅ 分析完成! 耗时: {duration:.1f} 秒")
        print(f"📁 结果目录: {self.output_dir}")
        print(f"   - 查重报告.xlsx/json/html")
        print(f"   - grading_results.json")
        print(f"   - feedback/*.md/html")
        print("="*60)

        return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='增强版实验报告查重与质量评估系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基础用法
  python tools/plagiarism_detection_enhanced.py

  # 指定实验目录
  python tools/plagiarism_detection_enhanced.py --experiment-dir "docs/teaching/2026-春季/汽服2302B班/07-car-gear"

  # 设置阈值和方法
  python tools/plagiarism_detection_enhanced.py --threshold 70 --method cosine

  # 指定模板文件
  python tools/plagiarism_detection_enhanced.py --template "docs/teaching/common/templates/实验报告模板.docx"

  # 仅执行查重
  python tools/plagiarism_detection_enhanced.py --plagiarism-only

  # 仅执行质量评估
  python tools/plagiarism_detection_enhanced.py --quality-only
        """
    )

    parser.add_argument(
        '--experiment-dir',
        type=Path,
        default=Path('docs/teaching/2026-春季/汽服2302B班/07-car-gear'),
        help='实验目录路径'
    )

    parser.add_argument(
        '--experiment-type',
        type=str,
        default='档位实验',
        choices=['档位实验', '转向灯实验'],
        help='实验类型'
    )

    parser.add_argument(
        '--class-name',
        type=str,
        default='汽服2302B班',
        help='班级名称'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=60.0,
        help='相似度可疑阈值 (0-100)'
    )

    parser.add_argument(
        '--method',
        type=str,
        default='hybrid',
        choices=['sequence', 'cosine', 'jaccard', 'levenshtein', 'hybrid'],
        help='相似度计算方法'
    )

    parser.add_argument(
        '--template',
        type=Path,
        help='模板文件路径（用于排除公共内容）'
    )

    parser.add_argument(
        '--no-template-filter',
        action='store_true',
        help='禁用模板过滤'
    )

    parser.add_argument(
        '--plagiarism-only',
        action='store_true',
        help='仅执行查重检测'
    )

    parser.add_argument(
        '--quality-only',
        action='store_true',
        help='仅执行质量评估'
    )

    parser.add_argument(
        '--output-formats',
        type=str,
        default='excel,json,html',
        help='输出报告格式（逗号分隔）'
    )

    args = parser.parse_args()

    # 转换方法
    method_map = {
        'sequence': SimilarityMethod.SEQUENCE,
        'cosine': SimilarityMethod.COSINE,
        'jaccard': SimilarityMethod.JACCARD,
        'levenshtein': SimilarityMethod.LEVENSHTEIN,
        'hybrid': SimilarityMethod.HYBRID
    }

    # 创建系统
    system = EnhancedPlagiarismSystem(
        experiment_dir=args.experiment_dir,
        experiment_type=args.experiment_type,
        class_name=args.class_name,
        threshold=args.threshold,
        method=method_map[args.method],
        use_template_filter=not args.no_template_filter,
        template_path=args.template
    )

    # 执行分析
    if args.plagiarism_only:
        # 仅查重
        if system.load_submissions():
            system.run_plagiarism_detection()
            system.generate_reports(args.output_formats.split(','))
    elif args.quality_only:
        # 仅质量评估
        if system.load_submissions():
            system.run_quality_assessment()
            system.save_quality_results()
    else:
        # 完整流程
        system.run_full_analysis()

    return 0


if __name__ == '__main__':
    sys.exit(main())
