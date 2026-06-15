# 查重系统迁移指南

## 概述

旧查重系统已被增强版新方案取代。新方案在功能、性能和可维护性方面均有显著提升。

## 方案对比

| 特性 | 旧方案 | 新方案 |
|------|----------------|-------------------|
| 相似度算法 | SequenceMatcher (1种) | 5种算法可选 |
| 模板过滤 | 无 | 智能排除 |
| 代码查重 | 无 | 专项检测 |
| 质量评估 | 无 | 6维度评估 |
| 报告格式 | Excel | Excel/JSON/HTML |
| 可视化 | 无 | 相似度矩阵 |
| 团伙检测 | 基础 | 增强版 |
| 代码结构 | 脚本 | 模块化 |

## 旧脚本状态

| 脚本 | 状态 | 替代方案 |
|------|------|----------|
| `tools/analyze_similarity.py` | **已废弃** | `tools/plagiarism_detection_enhanced.py` |
| `tools/fix_annotations.py` | **已废弃** | `tools/plagiarism_detection_enhanced.py` |
| `tools/update_xlsx_groups.py` | **保留** | 专门用于xlsx更新 |

## 迁移步骤

### 1. 基础查重（直接替代）

**旧用法：**
```bash
python tools/analyze_similarity.py
```

**新用法：**
```bash
python tools/plagiarism_detection_enhanced.py
```

### 2. 自定义阈值

**旧用法：**
```bash
# 需要修改脚本中的 threshold 值
```

**新用法：**
```bash
python tools/plagiarism_detection_enhanced.py --threshold 70
```

### 3. 不同算法

**新用法：**
```bash
python tools/plagiarism_detection_enhanced.py --method cosine
python tools/plagiarism_detection_enhanced.py --method hybrid
```

### 4. 仅查重（不评估质量）

**旧用法：**
```bash
python tools/analyze_similarity.py  # 仅查重功能
```

**新用法：**
```bash
python tools/plagiarism_detection_enhanced.py --plagiarism-only
```

### 5. 指定实验目录

**旧用法：**
```bash
# 需要修改脚本中的路径
```

**新用法：**
```bash
python tools/plagiarism_detection_enhanced.py \
    --experiment-dir "docs/teaching/2026-春季/汽服2302B班/07-car-gear"
```

## 新增功能

### 1. 模板过滤

使用模板文件排除公共内容：

```bash
python tools/plagiarism_detection_enhanced.py \
    --template "docs/teaching/common/templates/实验报告模板.docx"
```

### 2. 质量评估

新方案包含6维度质量评估：

```bash
python tools/plagiarism_detection_enhanced.py --quality-only
```

### 3. 多格式报告

指定输出格式：

```bash
python tools/plagiarism_detection_enhanced.py \
    --output-formats excel,json,html
```

### 4. 抄袭团伙检测

自动检测多人互抄团伙，结果在报告的"抄袭团伙"工作表中。

## 输出文件对比

### 旧方案

```
docs/teaching/.../docs/汽服2302B班_2026春季学期成绩册.xlsx  # 直接修改原文件
```

### 新方案

```
docs/teaching/.../results/
├── 查重报告.xlsx        # 独立报告，不修改原文件
├── 查重报告.json        # 结构化数据
├── 查重报告.html        # 可视化网页
└── quality_assessment.json  # 质量评估详情
```

## API 迁移

如果你在其他脚本中使用了旧函数：

### 旧 API

```python
from tools.analyze_similarity import (
    get_student_info,
    get_student_teams,
    find_similarity_groups
)
```

### 新 API

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
    group_info=group_info
)

# 执行检测
all_results, suspicious = detector.detect(submissions)
```

## 常见问题

### Q: 旧脚本还能用吗？
A: 可以，但不再维护。建议迁移到新方案。

### Q: 新方案的阈值如何设置？
A:
- 默认 60% 适用于大多数情况
- 严格检测：70-80%
- 宽松检测：50%

### Q: 如何选择算法？
A:
- `sequence`: 快速，适合短文本
- `cosine`: 长文本推荐
- `hybrid`: 综合性能最好（默认）

### Q: 旧数据会被覆盖吗？
A: 新方案生成独立报告文件，不会修改原文件。

## 完整示例

### 完整查重 + 质量评估

```bash
python tools/plagiarism_detection_enhanced.py \
    --experiment-dir "docs/teaching/2026-春季/汽服2302B班/07-car-gear" \
    --experiment-type "档位实验" \
    --class-name "汽服2302B班" \
    --threshold 60 \
    --method hybrid \
    --template "docs/teaching/common/templates/实验报告模板.docx" \
    --output-formats excel,json,html
```

### 仅查重

```bash
python tools/plagiarism_detection_enhanced.py \
    --plagiarism-only \
    --threshold 70
```

### 仅质量评估

```bash
python tools/plagiarism_detection_enhanced.py \
    --quality-only \
    --experiment-type "档位实验"
```
