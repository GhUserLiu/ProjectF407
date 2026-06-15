# -*- coding: utf-8 -*-
"""
差异高亮引擎
Diff Highlighter

计算文本差异并应用高亮样式
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import Enum
from difflib import SequenceMatcher, unified_diff


class DiffType(Enum):
    """差异类型"""
    IDENTICAL = 'identical'     # 完全相同
    SIMILAR = 'similar'         # 相似
    DELETED = 'deleted'         # 删除
    INSERTED = 'inserted'       # 插入
    REPLACED = 'replaced'       # 替换
    MOVED = 'moved'            # 移动


@dataclass
class DiffBlock:
    """差异块"""
    diff_type: DiffType
    text1: str                  # 文本1的内容
    text2: str                  # 文本2的内容
    position1: int              # 在文本1中的位置
    position2: int              # 在文本2中的位置
    similarity: float = 0.0     # 相似度（仅SIMILAR类型）


class DiffHighlighter:
    """差异高亮引擎"""

    # 高亮颜色
    HIGHLIGHT_COLORS = {
        'identical': '#d4edda',      # 绿色 - 完全相同
        'similar': '#fff3cd',        # 黄色 - 相似
        'deleted': '#f8d7da',        # 红色 - 删除
        'inserted': '#d1ecf1',       # 蓝色 - 插入
        'replaced': '#ffe5d0',       # 橙色 - 替换
        'moved': '#e2e3e5'           # 灰色 - 移动
    }

    def __init__(self, similar_threshold: float = 0.6):
        """
        初始化高亮器

        Args:
            similar_threshold: 相似度阈值
        """
        self.similar_threshold = similar_threshold

    def compute_diff(
        self,
        text1: str,
        text2: str,
        granularity: str = 'sentence'
    ) -> List[DiffBlock]:
        """
        计算文本差异

        Args:
            text1: 文本1
            text2: 文本2
            granularity: 粒度 ('sentence', 'paragraph', 'line')

        Returns:
            差异块列表
        """
        # 分割文本
        segments1 = self._split_text(text1, granularity)
        segments2 = self._split_text(text2, granularity)

        # 计算差异
        matcher = SequenceMatcher(None, segments1, segments2)
        blocks = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            seg1 = ' '.join(segments1[i1:i2])
            seg2 = ' '.join(segments2[j1:j2])

            diff_type = self._determine_diff_type(tag, seg1, seg2)

            blocks.append(DiffBlock(
                diff_type=diff_type,
                text1=seg1,
                text2=seg2,
                position1=i1,
                position2=j1,
                similarity=self._calculate_similarity(seg1, seg2) if diff_type == DiffType.SIMILAR else 0.0
            ))

        return blocks

    def _split_text(self, text: str, granularity: str) -> List[str]:
        """分割文本"""
        if granularity == 'line':
            return text.split('\n')
        elif granularity == 'paragraph':
            return re.split(r'\n\n+', text)
        elif granularity == 'sentence':
            # 按句子分割
            sentences = re.split(r'[。！？\n]+', text)
            return [s.strip() for s in sentences if s.strip()]
        else:
            return [text]

    def _determine_diff_type(self, tag: str, text1: str, text2: str) -> DiffType:
        """确定差异类型"""
        if tag == 'equal':
            return DiffType.IDENTICAL
        elif tag == 'replace':
            # 检查是否相似
            sim = self._calculate_similarity(text1, text2)
            if sim >= self.similar_threshold:
                return DiffType.SIMILAR
            return DiffType.REPLACED
        elif tag == 'delete':
            return DiffType.DELETED
        elif tag == 'insert':
            return DiffType.INSERTED
        else:
            return DiffType.REPLACED

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        return SequenceMatcher(None, text1, text2).ratio()

    def apply_highlighting(
        self,
        diff_blocks: List[DiffBlock],
        format: str = 'html'
    ) -> str:
        """
        应用高亮样式

        Args:
            diff_blocks: 差异块列表
            format: 输出格式 ('html', 'ansi')

        Returns:
            高亮后的文本
        """
        if format == 'html':
            return self._apply_html_highlighting(diff_blocks)
        elif format == 'ansi':
            return self._apply_ansi_highlighting(diff_blocks)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _apply_html_highlighting(self, diff_blocks: List[DiffBlock]) -> str:
        """应用HTML高亮"""
        lines = ['<div class="diff-container">']

        for block in diff_blocks:
            color = self.HIGHLIGHT_COLORS.get(block.diff_type.value, '#ffffff')
            css_class = f"diff-{block.diff_type.value}"

            if block.diff_type == DiffType.IDENTICAL:
                # 完全相同，显示一边
                lines.append(f'<div class="{css_class}" style="background-color: {color}; padding: 4px; margin: 2px 0;">')
                lines.append(f'  <span class="text">{self._escape_html(block.text1)}</span>')
                lines.append('</div>')

            elif block.diff_type == DiffType.SIMILAR:
                # 相似，并排显示
                lines.append(f'<div class="{css_class}" style="background-color: {color}; padding: 4px; margin: 2px 0;">')
                lines.append(f'  <div class="side1" style="width: 45%; display: inline-block;">{self._escape_html(block.text1)}</div>')
                lines.append(f'  <div class="similarity" style="width: 10%; display: inline-block; text-align: center;">{block.similarity:.0%}</div>')
                lines.append(f'  <div class="side2" style="width: 45%; display: inline-block;">{self._escape_html(block.text2)}</div>')
                lines.append('</div>')

            elif block.diff_type == DiffType.DELETED:
                lines.append(f'<div class="{css_class}" style="background-color: {color}; padding: 4px; margin: 2px 0;">')
                lines.append(f'  <span class="deleted">- {self._escape_html(block.text1)}</span>')
                lines.append('</div>')

            elif block.diff_type == DiffType.INSERTED:
                lines.append(f'<div class="{css_class}" style="background-color: {color}; padding: 4px; margin: 2px 0;">')
                lines.append(f'  <span class="inserted">+ {self._escape_html(block.text2)}</span>')
                lines.append('</div>')

            elif block.diff_type == DiffType.REPLACED:
                lines.append(f'<div class="{css_class}" style="background-color: {color}; padding: 4px; margin: 2px 0;">')
                lines.append(f'  <div class="side1" style="width: 45%; display: inline-block; color: #856404;">- {self._escape_html(block.text1)}</div>')
                lines.append(f'  <div class="side2" style="width: 45%; display: inline-block; color: #0c5460;">+ {self._escape_html(block.text2)}</div>')
                lines.append('</div>')

        lines.append('</div>')
        return '\n'.join(lines)

    def _apply_ansi_highlighting(self, diff_blocks: List[DiffBlock]) -> str:
        """应用终端高亮（ANSI转义码）"""
        # ANSI 颜色代码
        COLORS = {
            'identical': '\033[92m',    # 绿色
            'similar': '\033[93m',      # 黄色
            'deleted': '\033[91m',      # 红色
            'inserted': '\033[94m',     # 蓝色
            'replaced': '\033[95m',     # 紫色
            'reset': '\033[0m'
        }

        lines = []
        for block in diff_blocks:
            color = COLORS.get(block.diff_type.value, '')
            reset = COLORS['reset']

            if block.diff_type == DiffType.IDENTICAL:
                lines.append(f"{color}{block.text1}{reset}")
            elif block.diff_type == DiffType.SIMILAR:
                lines.append(f"{color}[相似 {block.similarity:.0%}]{block.text1} -> {block.text2}{reset}")
            elif block.diff_type == DiffType.DELETED:
                lines.append(f"{color}- {block.text1}{reset}")
            elif block.diff_type == DiffType.INSERTED:
                lines.append(f"{color}+ {block.text2}{reset}")
            elif block.diff_type == DiffType.REPLACED:
                lines.append(f"{color}- {block.text1} + {block.text2}{reset}")

        return '\n'.join(lines)

    def _escape_html(self, text: str) -> str:
        """转义HTML特殊字符"""
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        return text

    def highlight_similar_segments(
        self,
        segments1: List[str],
        segments2: List[str],
        threshold: float
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        高亮相似段落

        Args:
            segments1: 段落列表1
            segments2: 段落列表2
            threshold: 相似度阈值

        Returns:
            (高亮的段落1, 高亮的段落2)
        """
        highlighted1 = []
        highlighted2 = []

        for i, seg1 in enumerate(segments1):
            matched = False
            for j, seg2 in enumerate(segments2):
                sim = self._calculate_similarity(seg1, seg2)
                if sim >= threshold:
                    highlighted1.append({
                        'text': seg1,
                        'highlight': True,
                        'match_with': j,
                        'similarity': sim
                    })
                    highlighted2.append({
                        'text': seg2,
                        'highlight': True,
                        'match_with': i,
                        'similarity': sim
                    })
                    matched = True
                    break

            if not matched:
                highlighted1.append({
                    'text': seg1,
                    'highlight': False,
                    'match_with': None,
                    'similarity': 0.0
                })

        # 处理segments2中未匹配的段落
        matched_indices = {h['match_with'] for h in highlighted1 if h['match_with'] is not None}
        for j, seg2 in enumerate(segments2):
            if j not in matched_indices:
                highlighted2.append({
                    'text': seg2,
                    'highlight': False,
                    'match_with': None,
                    'similarity': 0.0
                })

        return highlighted1, highlighted2
