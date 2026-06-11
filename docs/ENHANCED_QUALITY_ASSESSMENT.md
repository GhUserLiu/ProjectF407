# 增强质量评估系统 v2.5.0

> 版本: 2.5.0 (2026-06-10)
> 新增: 代码深度分析、智能反馈建议、图像质量检测、评分一致性校验

## 概述

本系统是在原有查重与评分系统基础上的重大升级，提供了更全面、更智能的实验报告质量评估功能。

---

## 新增功能 (v2.5.0)

### 1. 代码深度分析器

**文件**: [tools/plagiarism/code_analyzer.py](tools/plagiarism/code_analyzer.py)

**功能特点**：
- 🔍 **语法正确性检查**：检测函数定义、参数类型、返回值
- 📊 **复杂度评估**：计算圈复杂度、代码行数、参数个数
- 📝 **命名规范检查**：检测函数命名、变量命名是否符合C语言规范
- ✅ **最佳实践验证**：检查HAL库使用、中断处理、消抖实现、状态机设计
- 🔒 **安全隐患检测**：检查数组越界、指针使用风险

**问题等级**：
| 等级 | 说明 | 扣分 |
|------|------|------|
| 🔴 CRITICAL | 严重错误，必须修复 | -15分 |
| 🟠 HIGH | 高优先级，强烈建议修复 | -10分 |
| 🟡 MEDIUM | 中等优先级，建议修复 | -5分 |
| 🟢 LOW | 低优先级，可以优化 | -2分 |
| 🔵 INFO | 信息提示 | 0分 |

**使用示例**：
```python
from tools.plagiarism import analyze_code_from_report

# 分析报告中的代码
result = analyze_code_from_report(report_text, "档位实验")

print(f"代码质量得分: {result.total_score}/{result.max_score}")
print(f"检测到问题: {len(result.issues)} 个")
print(f"代码亮点: {result.strengths}")
```

---

### 2. 智能反馈建议系统

**文件**: [tools/plagiarism/smart_feedback.py](tools/plagiarism/smart_feedback.py)

**功能特点**：
- 🎯 **针对性建议**：根据具体问题生成个性化改进建议
- 📚 **学习资源推荐**：推荐相关的文档、视频、教程
- 💻 **示例代码**：提供标准代码示例供参考
- 📖 **知识库驱动**：内置丰富的嵌入式开发知识库

**反馈类别**：
| 类别 | 说明 |
|------|------|
| TECHNICAL | 技术问题（GPIO、中断、DWT等） |
| STRUCTURE | 结构问题（流程图、章节等） |
| CODE | 代码问题（命名、注释等） |
| WRITING | 写作问题 |
| COMPLETENESS | 完整性问题 |

**使用示例**：
```python
from tools.plagiarism import generate_smart_feedback_report

# 生成智能反馈报告
feedback = generate_smart_feedback_report(
    student_id="2023001",
    name="张三",
    grading_result=grading_result,
    technical_check_result=technical_result,
    code_analysis_result=code_result
)

# 保存反馈
with open('feedback.md', 'w', encoding='utf-8') as f:
    f.write(feedback)
```

---

### 3. 图像质量检测模块

**文件**: [tools/plagiarism/image_quality_checker.py](tools/plagiarism/image_quality_checker.py)

**功能特点**：
- 📷 **分辨率检查**：检测图片是否清晰
- 🔍 **清晰度评估**：基于拉普拉斯方差评估图片模糊程度
- 📐 **宽高比分析**：识别电路图、代码截图等不同类型
- 💾 **文件大小检查**：建议压缩过大的图片文件
- 🔗 **相关性检测**：检查图片与实验内容的相关性

**质量等级**：
| 等级 | 说明 | 得分范围 |
|------|------|----------|
| 优秀 | 清晰、相关、规范 | 85-100 |
| 良好 | 基本符合要求 | 70-84 |
| 可接受 | 有小问题 | 50-69 |
| 差 | 存在明显问题 | 30-49 |
| 严重 | 需要重新拍摄 | 0-29 |

**使用示例**：
```python
from tools.plagiarism import ImageQualityChecker

# 检查报告中的图片
checker = ImageQualityChecker("档位实验")
result = checker.check_report_images(report_path)

print(f"检测到 {result.image_count} 张图片")
print(f"平均质量分: {result.total_score}")
print(f"质量等级: {result.quality_rating.value}")
```

---

### 4. 评分一致性校验

**文件**: [tools/plagiarism/grading_validator.py](tools/plagiarism/grading_validator.py)

**功能特点**：
- ✅ **评分标准验证**：检查rubric配置是否正确
- 👤 **单份评分验证**：检查分数范围、等级一致性
- 📊 **班级分布验证**：检查分数分布是否合理
- ⚠️ **异常分数预警**：识别需要人工复核的评分
- 💡 **改进建议生成**：提供针对性的改进建议

**检查项目**：
| 项目 | 说明 |
|------|------|
| 评分标准 | 总分、类别分值、关键词完整性 |
| 分数范围 | 0-100分检查、负数检查 |
| 等级一致性 | A/B/C/D/F等级与分数匹配检查 |
| 分数分布 | 班级平均分、标准差、等级比例检查 |
| 异常预警 | 满分预警、高抄袭风险预警 |

**使用示例**：
```python
from tools.plagiarism import validate_grading_results

# 执行评分校验
report = validate_grading_results(
    results=grading_results,
    rubric=rubric,
    output_dir=Path('results')
)

print(f"校验状态: {'通过' if report.validation_passed else '未通过'}")
print(f"问题数量: {report.issue_count}")
```

---

## 快速开始

### 安装依赖

```bash
# 核心依赖
pip install python-docx openpyxl jieba

# 可选依赖（增强功能）
pip install numpy Pillow sentence-transformers
```

### 基础用法

```bash
# 完整分析（所有新功能）
python tools/enhanced_quality_assessment.py

# 指定实验目录
python tools/enhanced_quality_assessment.py \
    --experiment-dir "docs/teaching/2026-春季/汽服2302B班/07-car-gear"

# 禁用某些功能
python tools/enhanced_quality_assessment.py \
    --no-code-analysis \
    --no-smart-feedback

# 仅执行评分校验
python tools/enhanced_quality_assessment.py \
    --validation-only
```

### 编程接口

```python
from tools.enhanced_quality_assessment import EnhancedQualityAssessmentSystem
from pathlib import Path

# 创建系统
system = EnhancedQualityAssessmentSystem(
    experiment_dir=Path("docs/teaching/2026-春季/汽服2302B班/07-car-gear"),
    experiment_type="档位实验",
    class_name="汽服2302B班",
    enable_code_analysis=True,
    enable_smart_feedback=True,
    enable_image_check=True,
    enable_validation=True
)

# 运行完整分析
system.run_full_analysis()
```

---

## 输出结果

### 文件结构

```
实验目录/results/
├── grading_validation_report.md       # 评分校验报告
├── grading_validation_report.json     # 校验数据
├── smart_feedback/                    # 智能反馈目录
│   ├── 2023001_张三_智能反馈.md
│   ├── 2023002_李四_智能反馈.md
│   └── ...
├── 查重报告.xlsx
├── 查重报告.json
├── 查重报告.html
└── grading_results.json
```

### 评分校验报告示例

```markdown
# 评分一致性验证报告

**验证时间**: 2026-06-10 22:30:15
**学生总数**: 35
**问题总数**: 5
**验证状态**: ✅ 通过

## 📊 统计信息

- 平均分: 78.5
- 分数范围: 45 - 98

等级分布:
  - A等: 6人 (17.1%)
  - B等: 15人 (42.9%)
  - C等: 10人 (28.6%)
  - D等: 3人 (8.6%)
  - F等: 1人 (2.9%)

## ⚠️ 问题统计

- 🔴 严重错误: 0个
- 🟠 错误: 0个
- 🟡 警告: 5个

## 💡 改进建议

1. 建议复核以下学生的评分: 20230015, 20230028
2. B等比例偏高，建议检查评分标准是否严格
```

### 智能反馈报告示例

```markdown
# 智能学习反馈报告

**学号**: 20230015
**姓名**: 张三
**总分**: 85.5/100 (85.5%)

---

## 📝 个性化改进建议

### 🔴 建议 1: DWT消抖实现缺失或不完整

[具体建议内容...]

**学习资源**:
- [DWT精确消抖实现](https://doc嵌入式.org/dwt-debounce) - DWT消抖完整教程

### 🟡 建议 2: 代码注释不足

[具体建议内容...]

## 📚 推荐学习资源

📄 [STM32 GPIO配置指南](https://doc嵌入式.org/gpio-guide)
   _GPIO工作原理和配置方法_
```

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                  增强质量评估系统 v2.5.0                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│  │ Rubric评分  │  │ 技术检查    │  │ 代码分析    │  │ 智能反馈    ││
│  │             │  │             │  │ (v2.5.0 新) │  │ (v2.5.0 新) ││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                    │
│  │ 图像检测    │  │ 评分校验    │  │ 报告生成    │                    │
│  │ (v2.5.0 新) │  │ (v2.5.0 新) │  │             │                    │
│  └─────────────┘  └─────────────┘  └─────────────┘                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 版本历史

### v2.5.0 (2026-06-10)
- ✨ 新增代码深度分析器
- ✨ 新增智能反馈建议系统
- ✨ 新增图像质量检测模块
- ✨ 新增评分一致性校验
- 🔧 优化评分反馈生成逻辑
- 📝 完善文档和使用示例

### v2.4.0 (2026-05-15)
- 新增配置化权重系统
- 增强语义检测
- 增强AI生成检测

### v2.1.0 (2026-05-01)
- 新增基于Rubric的详细评分
- 新增技术要点专项检查
- 新增学生个性化反馈生成

### v2.0.0 (2026-04-15)
- 初始版本
- 基础查重功能
