# -*- coding: utf-8 -*-
"""
对比视图生成器
Comparison View Generator

生成并排高亮相似内容的HTML视图
"""

from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from .diff_highlighter import DiffHighlighter, DiffBlock


class ComparisonViewGenerator:
    """对比视图生成器"""

    def __init__(
        self,
        output_dir: Path,
        template_theme: str = 'default'
    ):
        """
        初始化生成器

        Args:
            output_dir: 输出目录
            template_theme: 模板主题
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_theme = template_theme
        self.highlighter = DiffHighlighter()

    def generate_side_by_side_view(
        self,
        submission1: Dict,
        submission2: Dict,
        similarity_result: Optional[Dict] = None,
        granularity: str = 'sentence'
    ) -> Path:
        """
        生成并排对比HTML视图

        Args:
            submission1: 提交1 {'student_id': str, 'name': str, 'text': str}
            submission2: 提交2
            similarity_result: 相似度结果（可选）
            granularity: 文本分割粒度

        Returns:
            HTML文件路径
        """
        # 计算差异
        diff_blocks = self.highlighter.compute_diff(
            submission1['text'],
            submission2['text'],
            granularity
        )

        # 生成HTML
        html_content = self._generate_html(
            submission1,
            submission2,
            diff_blocks,
            similarity_result
        )

        # 保存文件
        filename = f"comparison_{submission1['student_id']}_{submission2['student_id']}.html"
        file_path = self.output_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return file_path

    def generate_unified_diff_view(
        self,
        text1: str,
        text2: str,
        output_name: str = 'unified_diff.html'
    ) -> Path:
        """
        生成统一差异视图

        Args:
            text1: 文本1
            text2: 文本2
            output_name: 输出文件名

        Returns:
            HTML文件路径
        """
        diff_blocks = self.highlighter.compute_diff(text1, text2, 'line')

        html_content = self._generate_unified_html(diff_blocks)

        file_path = self.output_dir / output_name

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return file_path

    def _generate_html(
        self,
        submission1: Dict,
        submission2: Dict,
        diff_blocks: List[DiffBlock],
        similarity_result: Optional[Dict]
    ) -> str:
        """生成并排对比HTML"""
        # 计算统计信息
        stats = self._calculate_stats(diff_blocks)

        # 生成HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>报告对比 - {submission1['name']} vs {submission2['name']}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 实验报告对比</h1>
            <div class="info">
                <div class="student-info">
                    <h3>学生1</h3>
                    <p>学号: {submission1['student_id']}</p>
                    <p>姓名: {submission1['name']}</p>
                </div>
                <div class="vs">VS</div>
                <div class="student-info">
                    <h3>学生2</h3>
                    <p>学号: {submission2['student_id']}</p>
                    <p>姓名: {submission2['name']}</p>
                </div>
            </div>
        </header>

        {self._generate_similarity_section(similarity_result)}

        <section class="stats">
            <h2>差异统计</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-value">{stats['total_blocks']}</div>
                    <div class="stat-label">总块数</div>
                </div>
                <div class="stat-item identical">
                    <div class="stat-value">{stats['identical']}</div>
                    <div class="stat-label">完全相同</div>
                </div>
                <div class="stat-item similar">
                    <div class="stat-value">{stats['similar']}</div>
                    <div class="stat-label">相似</div>
                </div>
                <div class="stat-item different">
                    <div class="stat-value">{stats['different']}</div>
                    <div class="stat-label">不同</div>
                </div>
            </div>
        </section>

        <section class="diff-content">
            <h2>详细对比</h2>
            {self._generate_diff_content(diff_blocks)}
        </section>

        <footer>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>由查重系统自动生成</p>
        </footer>
    </div>
</body>
</html>'''

        return html

    def _generate_unified_html(self, diff_blocks: List[DiffBlock]) -> str:
        """生成统一差异视图HTML"""
        content = self.highlighter.apply_highlighting(diff_blocks, 'html')

        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>统一差异视图</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', monospace;
            line-height: 1.6;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .diff-container {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .diff-identical {{ background-color: #d4edda; }}
        .diff-similar {{ background-color: #fff3cd; }}
        .diff-deleted {{ background-color: #f8d7da; }}
        .diff-inserted {{ background-color: #d1ecf1; }}
        .diff-replaced {{ background-color: #ffe5d0; }}
        .text {{ margin: 0; }}
    </style>
</head>
<body>
    <h1>统一差异视图</h1>
    {content}
</body>
</html>'''

    def _generate_similarity_section(self, similarity_result: Optional[Dict]) -> str:
        """生成相似度信息部分"""
        if not similarity_result:
            return ''

        return f'''
        <section class="similarity-info">
            <h2>相似度分析</h2>
            <div class="similarity-grid">
                <div class="similarity-item">
                    <div class="label">整体相似度</div>
                    <div class="value">{similarity_result.get('overall_similarity', 0):.1f}%</div>
                </div>
                <div class="similarity-item">
                    <div class="label">文本相似度</div>
                    <div class="value">{similarity_result.get('text_similarity', 0):.1f}%</div>
                </div>
                <div class="similarity-item">
                    <div class="label">代码相似度</div>
                    <div class="value">{similarity_result.get('code_similarity', 0):.1f}%</div>
                </div>
                <div class="similarity-item">
                    <div class="label">结构相似度</div>
                    <div class="value">{similarity_result.get('structure_similarity', 0):.1f}%</div>
                </div>
            </div>
        </section>'''

    def _generate_diff_content(self, diff_blocks: List[DiffBlock]) -> str:
        """生成差异内容"""
        lines = []

        for i, block in enumerate(diff_blocks):
            css_class = f"diff-{block.diff_type.value}"

            if block.diff_type.value == 'identical':
                lines.append(f'<div class="{css_class}">')
                lines.append(f'  <p>{self._escape_html(block.text1)}</p>')
                lines.append('</div>')

            elif block.diff_type.value == 'similar':
                lines.append(f'<div class="{css_class}">')
                lines.append(f'  <div class="side">')
                lines.append(f'    <p>{self._escape_html(block.text1)}</p>')
                lines.append(f'  </div>')
                lines.append(f'  <div class="similarity-score">{block.similarity:.0%}</div>')
                lines.append(f'  <div class="side">')
                lines.append(f'    <p>{self._escape_html(block.text2)}</p>')
                lines.append(f'  </div>')
                lines.append('</div>')

            else:
                lines.append(f'<div class="{css_class}">')
                if block.text1:
                    lines.append(f'  <p class="deleted">- {self._escape_html(block.text1)}</p>')
                if block.text2:
                    lines.append(f'  <p class="inserted">+ {self._escape_html(block.text2)}</p>')
                lines.append('</div>')

        return '\n'.join(lines)

    def _calculate_stats(self, diff_blocks: List[DiffBlock]) -> Dict:
        """计算统计信息"""
        stats = {
            'total_blocks': len(diff_blocks),
            'identical': 0,
            'similar': 0,
            'different': 0
        }

        for block in diff_blocks:
            if block.diff_type.value == 'identical':
                stats['identical'] += 1
            elif block.diff_type.value == 'similar':
                stats['similar'] += 1
            else:
                stats['different'] += 1

        return stats

    def _get_css(self) -> str:
        """获取CSS样式"""
        return '''
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }

        h1 {
            color: #333;
            margin-bottom: 20px;
        }

        .info {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .student-info {
            flex: 1;
        }

        .student-info h3 {
            color: #4CAF50;
            margin-bottom: 10px;
        }

        .student-info p {
            margin: 5px 0;
        }

        .vs {
            font-size: 24px;
            font-weight: bold;
            color: #FF9800;
            padding: 0 20px;
        }

        .similarity-info {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .similarity-info h2 {
            margin-bottom: 15px;
        }

        .similarity-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }

        .similarity-item {
            text-align: center;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }

        .similarity-item .label {
            color: #666;
            font-size: 14px;
        }

        .similarity-item .value {
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
            margin-top: 5px;
        }

        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }

        .stat-item {
            text-align: center;
            padding: 15px;
            border-radius: 5px;
        }

        .stat-item.identical {
            background-color: #d4edda;
        }

        .stat-item.similar {
            background-color: #fff3cd;
        }

        .stat-item.different {
            background-color: #f8d7da;
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
        }

        .stat-label {
            color: #666;
            margin-top: 5px;
        }

        .diff-content {
            background: white;
            padding: 20px;
            border-radius: 8px;
        }

        .diff-content h2 {
            margin-bottom: 15px;
        }

        .diff-identical {
            padding: 10px;
            margin: 5px 0;
            background-color: #d4edda;
            border-left: 4px solid #28a745;
        }

        .diff-similar {
            padding: 10px;
            margin: 5px 0;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            display: flex;
        }

        .diff-similar .side {
            flex: 1;
        }

        .diff-similar .similarity-score {
            flex: 0 0 80px;
            text-align: center;
            font-weight: bold;
            color: #856404;
        }

        .diff-deleted, .diff-inserted, .diff-replaced {
            padding: 10px;
            margin: 5px 0;
        }

        .diff-deleted {
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
        }

        .diff-inserted {
            background-color: #d1ecf1;
            border-left: 4px solid #17a2b8;
        }

        .diff-replaced {
            background-color: #ffe5d0;
            border-left: 4px solid #fd7e14;
        }

        .deleted {
            color: #721c24;
        }

        .inserted {
            color: #0c5460;
        }

        footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 14px;
        }

        @media (max-width: 768px) {
            .similarity-grid, .stat-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        '''

    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text
