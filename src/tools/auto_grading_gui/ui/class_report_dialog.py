#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
班级报告对话框
Class Report Dialog

显示图形化的班级批阅报告
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QScrollArea, QFrame, QSizePolicy,
    QSpacerItem, QWidget, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, QMargins
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap


class ClassReportDialog(QDialog):
    """班级报告对话框"""

    def __init__(self, class_name: str, experiment_id: str, parent=None):
        super().__init__(parent)

        self.class_name = class_name
        self.experiment_id = experiment_id
        self.grading_results: List[Dict] = []
        self.class_report: Dict = {}
        self._data_loaded = False
        self._updating_ui = False
        self._ui_initialized = False

        # 使用对话框类型，允许用户调整大小
        self.setWindowFlags(
            Qt.WindowType.Dialog |  # 对话框类型，可调整大小
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowMinimizeButtonHint
        )

        # 设置大小策略，允许拉伸
        self.setSizeGripEnabled(True)  # 启用右下角大小调整手柄

        # 设置大小约束策略
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred
        )

        # 设置模态行为
        self.setModal(True)  # 保持模态行为

        self.init_ui()
        self._ui_initialized = True
        self.load_report_data()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"班级报告 - {self.class_name}")
        self.setMinimumSize(1100, 750)

        # 恢复样式表（确认不是样式表导致的问题）
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f7fa;
            }
            QGroupBox {
                background-color: white;
                border: none;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #2c3e50;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # 标题区域
        title_widget = self.create_title_section()
        layout.addWidget(title_widget)

        # 统计卡片
        stats_widget = self.create_stats_section()
        layout.addWidget(stats_widget)

        # 主要内容区域（使用水平布局）
        content_layout = QHBoxLayout()

        # 左侧：图表
        charts_widget = self.create_charts_section()
        content_layout.addWidget(charts_widget, 4)

        # 右侧：排名表
        table_widget = self.create_table_section()
        content_layout.addWidget(table_widget, 6)

        layout.addLayout(content_layout)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def create_title_section(self) -> QFrame:
        """创建标题区域"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2ecc71);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        layout = QHBoxLayout()

        # 标题信息
        title_layout = QVBoxLayout()

        class_label = QLabel(self.class_name)
        class_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")

        exp_label = QLabel(self.experiment_id)
        exp_label.setStyleSheet("color: white; font-size: 16px;")

        title_layout.addWidget(class_label)
        title_layout.addWidget(exp_label)
        title_layout.addStretch()

        # 统计概览
        stats_layout = QHBoxLayout()

        self.overall_stats = {}

        stat_items = [
            ("total", "总人数", "0"),
            ("avg", "平均分", "0.0"),
            ("pass", "及格率", "0%"),
        ]

        for key, label, default in stat_items:
            stat_frame = QFrame()
            stat_frame.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.2);
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            stat_layout = QVBoxLayout()

            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: white; font-size: 12px;")
            label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            value_widget = QLabel(default)
            value_widget.setStyleSheet("color: white; font-size: 20px; font-weight: bold;")
            value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)

            stat_layout.addWidget(label_widget)
            stat_layout.addWidget(value_widget)
            stat_frame.setLayout(stat_layout)

            self.overall_stats[key] = value_widget
            stats_layout.addWidget(stat_frame)

        layout.addLayout(title_layout, 1)
        layout.addLayout(stats_layout)

        frame.setLayout(layout)
        return frame

    def create_stats_section(self) -> QFrame:
        """创建统计卡片区域"""
        frame = QFrame()
        frame.setStyleSheet("background-color: transparent;")
        layout = QGridLayout()
        layout.setSpacing(12)

        self.detail_stats = {}

        stats = [
            ("最高分", "max", "0", "#27ae60", "🏆"),
            ("最低分", "min", "0", "#e74c3c", "⚠️"),
            ("中位数", "median", "0", "#3498db", "📊"),
            ("标准差", "std", "0", "#9b59b6", "📈"),
            ("优秀率", "excellent", "0%", "#1abc9c", "⭐"),
            ("及格率", "pass", "0%", "#f39c12", "✓"),
        ]

        for i, (title, key, default, color, emoji) in enumerate(stats):
            card = QFrame()
            card.setMinimumHeight(95)
            card.setMinimumWidth(150)
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {color};
                    border-radius: 10px;
                    padding: 12px;
                }}
                QLabel {{
                    color: white;
                    background: transparent;
                    border: none;
                }}
            """)
            card_layout = QVBoxLayout()
            card_layout.setContentsMargins(8, 8, 8, 8)
            card_layout.setSpacing(4)

            # 图标和标题
            header_layout = QHBoxLayout()

            emoji_label = QLabel(emoji)
            emoji_label.setStyleSheet("font-size: 20px;")
            header_layout.addWidget(emoji_label)

            title_label = QLabel(title)
            title_label.setStyleSheet("font-size: 12px; font-weight: bold;")
            header_layout.addWidget(title_label)
            header_layout.addStretch()

            card_layout.addLayout(header_layout)

            # 数值
            value_label = QLabel(default)
            value_label.setStyleSheet("font-size: 22px; font-weight: bold;")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_label.setWordWrap(True)
            card_layout.addWidget(value_label)

            card.setLayout(card_layout)
            layout.addWidget(card, i // 3, i % 3)

            self.detail_stats[key] = value_label

        frame.setLayout(layout)
        return frame

    def create_charts_section(self) -> QGroupBox:
        """创建图表面板"""
        group = QGroupBox()
        group.setTitle("")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin-top: 12px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # 分数分布标题
        dist_title = QLabel("分数分布")
        dist_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding-bottom: 8px;
        """)
        layout.addWidget(dist_title)

        # 分数分布图表
        self.dist_chart = self.create_score_distribution_chart()
        layout.addWidget(self.dist_chart)

        # 评分类别标题
        cat_title = QLabel("评分类别平均分")
        cat_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding-bottom: 8px;
        """)
        layout.addWidget(cat_title)

        # 评分类别图表
        self.cat_chart = self.create_category_chart()
        layout.addWidget(self.cat_chart)

        layout.addStretch()
        group.setLayout(layout)
        return group

    def create_score_distribution_chart(self) -> QFrame:
        """创建分数分布图表"""
        frame = QFrame()
        frame.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
        """)
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.score_bars = {}

        ranges = [
            ("0-59", "#e74c3c", "不及格"),
            ("60-69", "#e67e22", "及格"),
            ("70-79", "#f1c40f", "中等"),
            ("80-89", "#2ecc71", "良好"),
            ("90-100", "#27ae60", "优秀"),
        ]

        for range_name, color, desc in ranges:
            bar_container = QWidget()
            bar_layout = QVBoxLayout()
            bar_layout.setSpacing(6)
            bar_layout.setContentsMargins(0, 0, 0, 0)

            # 顶部信息行
            info_layout = QHBoxLayout()

            # 范围标签
            label = QLabel(range_name)
            label.setProperty("scoreRange", color)  # 使用属性存储颜色
            label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
            # 使用 palette 而不是动态样式表
            palette = label.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
            label.setPalette(palette)
            label.setFixedWidth(70)

            # 描述标签
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("""
                color: #7f8c8d;
                font-size: 13px;
            """)
            desc_label.setFixedWidth(60)

            # 数量标签
            count_label = QLabel("0人")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("""
                color: #2c3e50;
                font-weight: bold;
                font-size: 14px;
            """)
            count_label.setFixedWidth(60)

            # 百分比标签
            percent_label = QLabel("0%")
            percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            percent_label.setProperty("scoreRange", color)
            percent_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                }
            """)
            palette2 = percent_label.palette()
            palette2.setColor(QPalette.ColorRole.WindowText, QColor(color))
            percent_label.setPalette(palette2)
            percent_label.setFixedWidth(50)

            info_layout.addWidget(label)
            info_layout.addWidget(desc_label)
            info_layout.addStretch()
            info_layout.addWidget(count_label)
            info_layout.addWidget(percent_label)

            bar_layout.addLayout(info_layout)

            # 进度条 - 使用简单的样式
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(24)
            progress_bar.setProperty("progressColor", color)

            # 使用通用样式
            progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #ecf0f1;
                    border: none;
                    border-radius: 12px;
                }
                QProgressBar::chunk {
                    background-color: #3498db;
                    border-radius: 12px;
                }
            """)

            bar_layout.addWidget(progress_bar)
            bar_container.setLayout(bar_layout)
            layout.addWidget(bar_container)

            # 存储进度条、标签和颜色引用
            self.score_bars[range_name] = (progress_bar, count_label, percent_label, color)

        frame.setLayout(layout)
        return frame

    def create_category_chart(self) -> QFrame:
        """创建评分类别图表"""
        frame = QFrame()
        frame.setStyleSheet("""
            background-color: #ffffff;
            border: 1px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
        """)
        layout = QVBoxLayout()
        layout.setSpacing(16)

        self.cat_bars = {}

        categories = [
            ("编译检查", "#3498db", "build"),
            ("代码质量", "#9b59b6", "code"),
            ("报告质量", "#e67e22", "report"),
        ]

        for cat_name, color, key in categories:
            bar_container = QWidget()
            bar_layout = QVBoxLayout()
            bar_layout.setSpacing(8)
            bar_layout.setContentsMargins(0, 0, 0, 0)

            # 顶部信息行
            info_layout = QHBoxLayout()

            # 类别标签
            label = QLabel(cat_name)
            label.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
            """)

            # 分数标签
            score_label = "--"
            score_value_label = QLabel(score_label)
            score_value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            score_value_label.setStyleSheet(f"""
                font-weight: bold;
                font-size: 16px;
                color: {color};
            """)
            score_value_label.setFixedWidth(80)

            info_layout.addWidget(label)
            info_layout.addStretch()
            info_layout.addWidget(score_value_label)

            bar_layout.addLayout(info_layout)

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(20)
            progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: #ecf0f1;
                    border: none;
                    border-radius: 10px;
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {color}, stop:1 {color.replace('6', '7')});
                    border-radius: 10px;
                }}
            """)

            bar_layout.addWidget(progress_bar)
            bar_container.setLayout(bar_layout)
            layout.addWidget(bar_container)

            self.cat_bars[key] = (progress_bar, score_value_label)

        frame.setLayout(layout)
        return frame

    def create_table_section(self) -> QGroupBox:
        """创建表格面板"""
        group = QGroupBox()
        group.setTitle("")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin-top: 12px;
                padding: 20px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(12)

        # 表格标题
        table_title = QLabel("学生排名")
        table_title.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #2c3e50;
            padding-bottom: 8px;
        """)
        layout.addWidget(table_title)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["排名", "学号", "姓名", "得分", "等级"])

        # 表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 10px;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
        """)

        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 排名
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # 学号
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 姓名
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 得分
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 等级

        # 设置最小列宽，确保数据可见
        self.table.setColumnWidth(0, 60)   # 排名
        self.table.setColumnWidth(1, 100)  # 学号
        self.table.setColumnWidth(2, 80)   # 姓名
        self.table.setColumnWidth(3, 80)   # 得分
        self.table.setColumnWidth(4, 60)   # 等级

        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)

        layout.addWidget(self.table)
        group.setLayout(layout)
        return group

    def load_report_data(self):
        """加载报告数据"""
        # 防止重复加载
        if self._updating_ui:
            return

        self._updating_ui = True

        try:
            # 禁用UI更新，防止闪烁
            self.setUpdatesEnabled(False)

            # 构建报告目录路径
            report_dir = Path("outputs/grading") / self.class_name / self.experiment_id

            print(f"[ClassReportDialog] 加载报告数据: {report_dir}")

            # 读取班级报告
            class_report_path = report_dir / "批阅汇总.json"
            if class_report_path.exists():
                try:
                    with open(class_report_path, 'r', encoding='utf-8') as f:
                        self.class_report = json.load(f)
                    print(f"[ClassReportDialog] 班级报告加载成功: {len(self.class_report.get('grading_results', []))} 条记录")
                except Exception as e:
                    print(f"[ClassReportDialog] 读取班级报告失败: {e}")
                    self.class_report = {}
            else:
                print(f"[ClassReportDialog] 班级报告文件不存在: {class_report_path}")
                self.class_report = {}

            # 读取个人报告
            self.grading_results = []
            individuals_dir = report_dir / "个人报告"
            if individuals_dir.exists():
                report_files = list(individuals_dir.glob("*-评分.json"))
                print(f"[ClassReportDialog] 找到 {len(report_files)} 个个人报告文件")

                for report_file in report_files:
                    try:
                        with open(report_file, 'r', encoding='utf-8') as f:
                            result = json.load(f)
                            self.grading_results.append(result)
                    except Exception as e:
                        print(f"[ClassReportDialog] 读取个人报告失败 {report_file}: {e}")
            else:
                print(f"[ClassReportDialog] 个人报告目录不存在: {individuals_dir}")

            print(f"[ClassReportDialog] 共加载 {len(self.grading_results)} 个学生记录")

            # 按分数排序
            self.grading_results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

            # 更新UI
            self.update_stats()
            self.update_charts()
            self.update_ranking_table()

        finally:
            # 重新启用UI更新
            self.setUpdatesEnabled(True)
            self._updating_ui = False

    def update_stats(self):
        """更新统计信息"""
        if not self.class_report and not self.grading_results:
            print("[ClassReportDialog] 没有数据可更新统计")
            return

        stats = self.class_report.get('statistics', {})

        # 总人数
        total = len(self.grading_results)
        self.overall_stats["total"].setText(str(total))

        # 平均分
        average = stats.get('average_score', 0)
        try:
            avg_value = float(average)
            self.overall_stats["avg"].setText(f"{avg_value:.1f}")
        except (ValueError, TypeError):
            self.overall_stats["avg"].setText("0.0")

        # 及格率
        if self.grading_results:
            scores = []
            for r in self.grading_results:
                try:
                    score = float(r.get('total_score', 0))
                    scores.append(score)
                except (ValueError, TypeError):
                    scores.append(0.0)

            passed = sum(1 for s in scores if s >= 60)
            pass_rate = (passed / total * 100) if total > 0 else 0
            self.overall_stats["pass"].setText(f"{pass_rate:.1f}%")

            # 详细统计
            if total > 0:
                max_score = max(scores) if scores else 0
                min_score = min(scores) if scores else 0

                self.detail_stats["max"].setText(f"{max_score:.1f}")
                self.detail_stats["min"].setText(f"{min_score:.1f}")

                # 中位数
                scores_sorted = sorted(scores)
                n = len(scores_sorted)
                if n % 2 == 0:
                    median = (scores_sorted[n//2 - 1] + scores_sorted[n//2]) / 2
                else:
                    median = scores_sorted[n//2]
                self.detail_stats["median"].setText(f"{median:.1f}")

                # 标准差
                if n > 1:
                    variance = sum((x - avg_value) ** 2 for x in scores) / n
                    std_dev = variance ** 0.5 if variance >= 0 else 0
                    self.detail_stats["std"].setText(f"{std_dev:.1f}")
                else:
                    self.detail_stats["std"].setText("0.0")

                # 优秀率
                excellent = sum(1 for s in scores if s >= 80)
                excellent_rate = (excellent / total * 100) if total > 0 else 0
                self.detail_stats["excellent"].setText(f"{excellent_rate:.0f}%")

                # 及格率
                self.detail_stats["pass"].setText(f"{pass_rate:.0f}%")

    def update_charts(self):
        """更新图表"""
        if not self.grading_results:
            return

        total = len(self.grading_results)
        if total == 0:
            return

        # 更新分数分布
        score_ranges = {
            "0-59": 0,
            "60-69": 0,
            "70-79": 0,
            "80-89": 0,
            "90-100": 0,
        }

        for result in self.grading_results:
            score = result.get('total_score', 0)
            if score < 60:
                score_ranges["0-59"] += 1
            elif score < 70:
                score_ranges["60-69"] += 1
            elif score < 80:
                score_ranges["70-79"] += 1
            elif score < 90:
                score_ranges["80-89"] += 1
            else:
                score_ranges["90-100"] += 1

        for range_name, (progress_bar, count_label, percent_label, color) in self.score_bars.items():
            count = score_ranges.get(range_name, 0)
            percentage = (count / total * 100) if total > 0 else 0

            # 使用 setValue 而不是 setFixedWidth
            progress_bar.setValue(int(percentage))
            count_label.setText(f"{count}人")
            percent_label.setText(f"{percentage:.0f}%")

            # 只设置一次样式，避免重复设置导致闪烁
            if not hasattr(progress_bar, '_style_set'):
                progress_bar.setStyleSheet(f"""
                    QProgressBar {{
                        background-color: #ecf0f1;
                        border: none;
                        border-radius: 12px;
                    }}
                    QProgressBar::chunk {{
                        background-color: {color};
                        border-radius: 12px;
                    }}
                """)
                progress_bar._style_set = True

        # 更新评分类别
        category_scores = {
            "build": [],
            "code": [],
            "report": []
        }

        for result in self.grading_results:
            for category_score in result.get('category_scores', []):
                category_id = category_score.get('category_id', '')
                earned_points = category_score.get('earned_points', 0)
                max_points = category_score.get('max_points', 1)

                # 映射category_id到key
                key_map = {
                    "compilation": "build",
                    "code_quality": "code",
                    "report_quality": "report"
                }

                mapped_key = key_map.get(category_id)
                if mapped_key and mapped_key in category_scores:
                    percentage_score = (earned_points / max_points * 100) if max_points > 0 else 0
                    category_scores[mapped_key].append(percentage_score)

        for key, (progress_bar, score_label) in self.cat_bars.items():
            scores = category_scores.get(key, [])
            if scores:
                avg_score = sum(scores) / len(scores)
                progress_bar.setValue(int(avg_score))
                score_label.setText(f"{avg_score:.0f}")
            else:
                progress_bar.setValue(0)
                score_label.setText("--")

    def update_ranking_table(self):
        """更新排名表格"""
        self.table.setRowCount(len(self.grading_results))

        for row, result in enumerate(self.grading_results):
            # 确保result是字典类型
            if not isinstance(result, dict):
                continue

            # 排名
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 前三名特殊样式
            if row < 3:
                rank_item.setBackground(QColor("#f39c12"))
                rank_item.setForeground(QColor("white"))

            self.table.setItem(row, 0, rank_item)

            # 学号
            student_id = result.get('student_id', '')
            id_item = QTableWidgetItem(str(student_id))
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, id_item)

            # 姓名
            name = result.get('name', '')
            name_item = QTableWidgetItem(str(name))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, name_item)

            # 得分
            score = result.get('total_score', 0)
            try:
                score_value = float(score)
                score_item = QTableWidgetItem(f"{score_value:.1f}")
            except (ValueError, TypeError):
                score_item = QTableWidgetItem("0.0")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 得分颜色编码
            try:
                if score_value >= 90:
                    score_item.setBackground(QColor("#27ae60"))
                    score_item.setForeground(QColor("white"))
                elif score_value >= 80:
                    score_item.setBackground(QColor("#2ecc71"))
                    score_item.setForeground(QColor("white"))
                elif score_value >= 70:
                    score_item.setBackground(QColor("#f1c40f"))
                elif score_value >= 60:
                    score_item.setBackground(QColor("#e67e22"))
                    score_item.setForeground(QColor("white"))
                else:
                    score_item.setBackground(QColor("#e74c3c"))
                    score_item.setForeground(QColor("white"))
            except:
                pass  # 保持默认样式

            self.table.setItem(row, 3, score_item)

            # 等级
            grade = result.get('grade', 'N/A')
            grade_item = QTableWidgetItem(str(grade))
            grade_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # 等级颜色
            grade_colors = {
                'A': "#27ae60",
                'B': "#2ecc71",
                'C': "#f1c40f",
                'D': "#e67e22",
                'F': "#e74c3c"
            }
            if grade in grade_colors:
                grade_item.setBackground(QColor(grade_colors[grade]))
                grade_item.setForeground(QColor("white"))

            self.table.setItem(row, 4, grade_item)
