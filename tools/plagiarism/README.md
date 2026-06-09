# 增强版实验报告查重与质量评估系统

> 版本: 2.0.0
> 作者: STM32F407 教学团队

## 功能概述

本系统提供全面的实验报告查重和质量评估功能，支持：

### 核心功能

| 功能 | 描述 |
|------|------|
| **多算法查重** | 支持 Sequence、Cosine、Jaccard、Levenshtein、混合算法 |
| **模板排除** | 自动识别并排除报告模板中的公共内容 |
| **代码查重** | 专项检测代码块相似度 |
| **小组识别** | 自动识别小组归属，区分同组合作与跨组抄袭 |
| **质量评估** | 6维度质量评估（技术准确性、完整性、分析深度等） |
| **详细报告** | 生成 Excel、JSON、HTML 格式报告 |
| **相似度矩阵** | 可视化学生间相似度热力图 |
| **抄袭团伙** | 自动检测多人互抄团伙 |

## 快速开始

### 安装依赖

```bash
pip install openpyxl python-docx
```

### 基础用法

```bash
# 默认配置运行
python tools/plagiarism_detection_enhanced.py

# 指定实验目录
python tools/plagiarism_detection_enhanced.py --experiment-dir "docs/teaching/2026-春季/汽服2302B班/07-car-gear"

# 设置可疑阈值和方法
python tools/plagiarism_detection_enhanced.py --threshold 70 --method cosine
```

### 命令行参数

```
--experiment-dir     实验目录路径（默认: docs/teaching/2026-春季/汽服2302B班/07-car-gear）
--experiment-type    实验类型（档位实验/转向灯实验）
--class-name         班级名称
--threshold          相似度可疑阈值 0-100（默认: 60）
--method             相似度计算方法（sequence/cosine/jaccard/levenshtein/hybrid）
--template           模板文件路径
--no-template-filter 禁用模板过滤
--plagiarism-only    仅执行查重检测
--quality-only       仅执行质量评估
--output-formats     输出报告格式（excel,json,html）
```

## 输出说明

### 文件结构

```
实验目录/
└── results/
    ├── 查重报告.xlsx       # Excel 详细报告
    ├── 查重报告.json       # JSON 数据报告
    ├── 查重报告.html       # HTML 可视化报告
    └── quality_assessment.json  # 质量评估详情
```

### Excel 报告包含

| 工作表 | 内容 |
|--------|------|
| 汇总 | 统计信息摘要 |
| 详细结果 | 所有高相似度对详情 |
| 相似度矩阵 | 学生间相似度热力图 |
| 抄袭团伙 | 检测到的抄袭团伙 |
| 统计分析 | 相似度分布统计 |

## 模块架构

```
tools/plagiarism/
├── __init__.py           # 模块入口
├── core.py               # 核心查重逻辑
├── algorithms.py         # 相似度算法实现
├── template.py           # 模板内容排除
├── quality.py            # 质量评估模块
└── report.py             # 报告生成器
```

### API 使用示例

```python
from tools.plagiarism import (
    PlagiarismDetector,
    SimilarityMethod,
    PlagiarismReport
)

# 创建检测器
detector = PlagiarismDetector(
    method=SimilarityMethod.HYBRID,
    threshold=60.0,
    group_info={'学生1': '组1', '学生2': '组2'}
)

# 执行检测
submissions = {
    '2023001': {'name': '张三', 'text': '报告内容...'},
    '2023002': {'name': '李四', 'text': '报告内容...'}
}

all_results, suspicious = detector.detect(submissions)

# 生成报告
from tools.plagiarium.report import ReportConfig
config = ReportConfig(output_dir=Path('results'))
report = PlagiarismReport(config)
report.add_results(all_results, suspicious)
report.generate_excel()
```

## 算法说明

### 1. 相似度算法

| 算法 | 适用场景 | 特点 |
|------|----------|------|
| Sequence | 短文本、精确匹配 | 基于序列匹配，快速 |
| Cosine | 长文本 | TF-IDF 余弦相似度 |
| Jaccard | 集合相似度 | 词语重叠度 |
| Levenshtein | 编辑距离 | 字符变化检测 |
| Hybrid | 综合评估 | 加权混合多种算法 |

### 2. 质量评估维度

| 维度 | 权重 | 检查内容 |
|------|------|----------|
| 技术准确性 | 30% | 技术要点正确性 |
| 内容完整性 | 25% | 章节完整性 |
| 分析深度 | 15% | 内容分析深度 |
| 写作质量 | 10% | 结构、格式、排版 |
| 代码质量 | 10% | 注释、命名规范 |
| 原创性 | 10% | 抄袭风险评估 |

### 3. 模板过滤原理

1. **模板提取**: 从模板文件或多份报告中提取高频模式
2. **模式匹配**: 使用正则表达式匹配模板内容
3. **内容过滤**: 在查重前排除模板内容
4. **智能识别**: 区分模板内容和原创内容

## 最佳实践

### 1. 提高查重准确性

```bash
# 使用模板文件排除公共内容
python tools/plagiarism_detection_enhanced.py \
    --template "docs/teaching/common/templates/实验报告模板.docx"

# 调整阈值
python tools/plagiarism_detection_enhanced.py --threshold 70

# 使用混合算法
python tools/plagiarism_detection_enhanced.py --method hybrid
```

### 2. 处理不同实验类型

```bash
# 档位实验
python tools/plagiarism_detection_enhanced.py \
    --experiment-type "档位实验" \
    --experiment-dir "docs/teaching/.../07-car-gear"

# 转向灯实验
python tools/plagiarism_detection_enhanced.py \
    --experiment-type "转向灯实验" \
    --experiment-dir "docs/teaching/.../01-turn-signal"
```

### 3. 独立运行各个模块

```bash
# 仅查重
python tools/plagiarism_detection_enhanced.py --plagiarism-only

# 仅质量评估
python tools/plagiarism_detection_enhanced.py --quality-only

# 指定输出格式
python tools/plagiarism_detection_enhanced.py --output-formats excel,json
```

## 常见问题

### Q: 如何判断是否抄袭？
A: 系统综合判断以下因素：
- 相似度是否超过阈值（默认 60%）
- 是否跨组（同组允许一定相似度）
- 共享段落数量
- 代码相似度

### Q: 为什么需要模板过滤？
A: 报告模板包含公共内容（如标题、要求说明），不排除会导致虚高相似度。

### Q: 质量评估的 AI 置信度是什么？
A: 表示评估结果的可信程度（0-1），基于评估完整性和数据质量。

### Q: 如何自定义技术检查点？
A: 编辑 `tools/plagiarism/quality.py` 中的 `TechnicalValidator.TECHNICAL_CHECKS`。

## 更新日志

### v2.0.0 (2024-06)
- 重构为模块化架构
- 新增多算法支持
- 新增模板过滤功能
- 新增质量评估模块
- 新增相似度矩阵可视化
- 新增抄袭团伙检测

### v1.0.0 (2024-05)
- 初始版本
- 基础查重功能
- Excel 报告生成
