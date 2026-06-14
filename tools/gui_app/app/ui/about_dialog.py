"""
关于对话框模块

显示软件信息、作者信息和鸣谢
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QScrollArea, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("关于 STM32教学管理系统")
        self.setMinimumSize(600, 500)
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建选项卡
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e9ecef;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                font-weight: bold;
            }
        """)

        # 关于页面
        about_page = self._create_about_page()
        tabs.addTab(about_page, "关于")

        # 作者页面
        author_page = self._create_author_page()
        tabs.addTab(author_page, "作者")

        # 鸣谢页面
        thanks_page = self._create_thanks_page()
        tabs.addTab(thanks_page, "鸣谢")

        # 许可证页面
        license_page = self._create_license_page()
        tabs.addTab(license_page, "许可证")

        layout.addWidget(tabs)

        # 关闭按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("关闭")
        close_button.setMinimumWidth(100)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

    def _create_about_page(self) -> QWidget:
        """创建关于页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel("STM32教学管理系统")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel("版本 2.7.0")
        version_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #6c757d;
            }
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        # 图标占位
        icon_label = QLabel("🎓")
        icon_label.setStyleSheet("font-size: 80px;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # 描述
        description = QLabel(
            "一款专为STM32嵌入式教学设计的综合性管理工具。\n"
            "集成了查重检测、自动评分、反馈生成和报告输出等功能，\n"
            "帮助教师高效管理学生实验作业。"
        )
        description.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #495057;
                line-height: 1.6;
            }
        """)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)

        # 主要功能
        features_label = QLabel()
        features_label.setText(
            "<b>主要功能：</b><br>"
            "• 🔍 智能查重检测 - 支持文本、代码和语义相似度分析<br>"
            "• 📝 自动评分评估 - 基于评分标准的智能评分系统<br>"
            "• 💬 智能反馈生成 - 为学生生成个性化的改进建议<br>"
            "• 📄 报告输出 - 自动生成Excel格式的分析报告<br>"
            "• 🏫 多班级处理 - 批量处理多个班级的作业"
        )
        features_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #495057;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
            }
        """)
        features_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(features_label)

        # 技术栈
        tech_label = QLabel()
        tech_label.setText(
            "<b>技术栈：</b> Python · PyQt6 · sentence-transformers · jieba · openpyxl"
        )
        tech_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #6c757d;
                padding-top: 10px;
            }
        """)
        tech_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tech_label)

        layout.addStretch()
        return widget

    def _create_author_page(self) -> QWidget:
        """创建作者页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        title = QLabel("开发团队")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 作者信息卡片
        author_info = QLabel()
        author_info.setText("""
<div style="text-align: center; padding: 20px;">
    <h3 style="color: #2c3e50;">作者</h3>
    <p style="font-size: 16px; color: #495057;">
        <b>刘兆骐</b><br>
        <span style="color: #6c757d;">山西工程科技职业大学<br>汽车工程学院 · 助教</span>
    </p>

    <h3 style="color: #2c3e50; margin-top: 30px;">技术支持</h3>
    <p style="font-size: 16px; color: #495057;">
        <b>Claude (Anthropic)</b><br>
        <span style="color: #6c757d;">代码生成 · 算法优化 · 测试验证</span>
    </p>

    <h3 style="color: #2c3e50; margin-top: 30px;">特别致谢</h3>
    <p style="font-size: 14px; color: #6c757d;">
        感谢所有参与测试的师生们提出的宝贵意见和建议
    </p>
</div>
        """)
        author_info.setWordWrap(True)
        layout.addWidget(author_info)

        # 联系方式
        contact = QLabel()
        contact.setText("""
<div style="text-align: center; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
    <p style="margin: 0; color: #495057;">
        <b>联系方式：</b><br>
        <a href="mailto:liuzhaoqi@sxgkd.edu.cn" style="color: #3498db;">
            📧 liuzhaoqi@sxgkd.edu.cn
        </a><br>
        <span style="font-size: 12px; color: #6c757d;">
            如使用中发现故障，请提供触发故障的行为及故障现象，通过邮箱与作者联系
        </span>
    </p>
    <p style="margin: 10px 0 0 0; color: #495057;">
        <b>项目地址：</b><br>
        <a href="https://github.com/GhUserLiu/ProjectF407" style="color: #3498db;">
            github.com/GhUserLiu/ProjectF407
        </a>
    </p>
</div>
        """)
        contact.setOpenExternalLinks(True)
        contact.setWordWrap(True)
        layout.addWidget(contact)

        layout.addStretch()
        return widget

    def _create_thanks_page(self) -> QWidget:
        """创建鸣谢页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # 标题
        title = QLabel("测试鸣谢")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QScrollArea.Shape.NoFrame)

        # 内容
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(10)

        # 添加班级信息
        classes = [
            {
                "name": "汽服2301B班",
                "period": "2025-2026学年 第二学期",
                "contribution": "首批测试用户，参与STM32嵌入式实验课程的完整测试，提交了多份实验报告，帮助发现并修复了多个关键问题"
            },
            {
                "name": "汽服2302B班",
                "period": "2025-2026学年 第二学期",
                "contribution": "参与系统全面测试，验证了查重检测、自动评分和反馈生成等功能的准确性和实用性，提供了宝贵的改进建议"
            }
        ]

        for cls in classes:
            card = QLabel(f"""
<div style="
    padding: 15px;
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    border-radius: 5px;
">
    <h4 style="color: #2c3e50; margin: 0 0 5px 0;">📚 {cls['name']}</h4>
    <p style="color: #6c757d; margin: 5px 0; font-size: 13px;">
        <b>测试时间：</b>{cls['period']}
    </p>
    <p style="color: #495057; margin: 5px 0; font-size: 13px;">
        <b>贡献：</b>{cls['contribution']}
    </p>
</div>
            """)
            card.setWordWrap(True)
            content_layout.addWidget(card)

        # 技术鸣谢
        tech_card = QLabel("""
<div style="
    padding: 15px;
    background-color: #e8f5e9;
    border-left: 4px solid #4caf50;
    border-radius: 5px;
">
    <h4 style="color: #2e7d32; margin: 0 0 10px 0;">🛠️ 技术鸣谢</h4>
    <p style="color: #495057; margin: 5px 0; font-size: 13px;">
        本项目使用了以下开源技术和库：
    </p>
    <ul style="color: #495057; margin: 5px 0 0 20px; font-size: 13px;">
        <li>PyQt6 - Qt框架的Python绑定</li>
        <li>sentence-transformers - 语义相似度分析</li>
        <li>jieba - 中文分词</li>
        <li>openpyxl - Excel文件处理</li>
        <li>python-docx - Word文档处理</li>
    </ul>
</div>
        """)
        tech_card.setWordWrap(True)
        content_layout.addWidget(tech_card)

        content_layout.addStretch()
        scroll.setWidget(content)

        layout.addWidget(scroll)
        return widget

    def _create_license_page(self) -> QWidget:
        """创建许可证页面"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title = QLabel("开源许可证")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 许可证内容
        license_text = QTextEdit()
        license_text.setReadOnly(True)
        license_text.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
            }
        """)
        license_text.setHtml("""
<div style="text-align: center;">
    <h2 style="color: #2c3e50;">MIT License</h2>

    <p style="text-align: left; color: #495057; line-height: 1.6;">
    Copyright (c) 2025-2026 刘兆骐
    </p>

    <p style="text-align: left; color: #495057; line-height: 1.6;">
    特此授予任何人获得本软件和相关文档文件的副本，无需限制地处理本软件，
    包括但不限于使用、复制、修改、合并、发布、分发、再许可和/或出售本软件副本，
    并允许获得本软件的人员这样做，但须符合以下条件：
    </p>

    <p style="text-align: left; color: #495057; line-height: 1.6;">
    上述版权声明和本许可声明应包含在本软件的所有副本或实质性部分中。
    </p>

    <p style="text-align: left; color: #495057; line-height: 1.6;">
    本软件按"原样"提供，不提供任何形式的明示或暗示保证，包括但不限于
    对适销性、适用性和非侵权的保证。在任何情况下，作者或版权持有人均不对
    任何索赔、损害或其他责任负责，无论是由于合同、侵权或其他方式引起的，
    由本软件或本软件的使用或其他交易引起。
    </p>

    <hr style="margin: 20px 0;">

    <h3 style="color: #2c3e50;">第三方库许可证</h3>
    <p style="text-align: left; color: #495057; line-height: 1.6;">
    本项目使用的第三方库均遵循其各自的开源许可证：
    </p>
    <ul style="text-align: left; color: #495057;">
        <li>PyQt6 - GPL v3 / Commercial</li>
        <li>sentence-transformers - Apache 2.0</li>
        <li>jieba - MIT</li>
        <li>openpyxl - MIT</li>
        <li>python-docx - MIT</li>
    </ul>
</div>
        """)
        layout.addWidget(license_text)

        return widget
