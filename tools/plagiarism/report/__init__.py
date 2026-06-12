"""
报告生成模块
Report Generation Module

生成 Excel、HTML、JSON 格式的报告
"""

from .report import (
    PlagiarismReport,
    ReportConfig,
    generate_excel_report,
    generate_html_report
)

__all__ = [
    'PlagiarismReport',
    'ReportConfig',
    'generate_excel_report',
    'generate_html_report',
]
