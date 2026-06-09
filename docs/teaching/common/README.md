# 通用评估脚本

本文件夹包含用于评估学生实验报告的通用脚本和模板。

## 文件说明

### 脚本 (scripts/)

| 脚本 | 功能 |
|------|------|
| `main.py` | 主程序：提取学生ZIP文件，创建学生列表 |
| `extract_content.py` | 从Word文档中提取文本内容 |
| `evaluate.py` | 根据评分标准评估报告 |
| `quality_assessment.py` | 质量评估与抄袭检测 |
| `generate_output.py` | 生成教师评分表和学生反馈文档 |

### 模板 (templates/)

| 文件 | 说明 |
|------|------|
| `实验报告模板.md` | Markdown格式的实验报告模板 |
| `实验报告模板.docx` | Word格式的实验报告模板 |

### 评分标准 (rubrics/)

| 文件 | 说明 |
|------|------|
| `rubric.json` | 评分标准和参考答案 |

## 使用流程

### 1. 准备工作

确保实验文件夹结构正确：
```
assignments/2026-春季/汽服2302B班/07-car-gear/
├── submissions/    # 放置学生提交的ZIP文件
├── processed/      # 自动生成：评估数据
├── feedback/       # 自动生成：学生反馈
├── results/        # 自动生成：教师评分表
├── task.md         # 任务书
└── README.md       # 实验说明
```

### 2. 运行评估脚本

```bash
cd assignments/2026-春季/汽服2302B班/07-car-gear/

# 步骤1：提取学生报告（如果有ZIP文件）
python ../../common/scripts/main.py

# 步骤2：提取内容
python ../../common/scripts/extract_content.py

# 步骤3：评估报告
python ../../common/scripts/evaluate.py

# 步骤4：生成输出
python ../../common/scripts/generate_output.py
```

### 3. 查看结果

- **教师评分表**：`results/汽服2302B班_07_档位实验_评分表.xlsx`
- **学生反馈**：`feedback/` 文件夹中的学生反馈文档

## 自定义评分标准

编辑 `rubrics/rubric.json` 文件来修改评分标准：

```json
{
  "categories": [
    {
      "id": "category_name",
      "name": "分类名称",
      "points": 分值,
      "criteria": [
        {
          "description": "评分项描述",
          "points": 分值,
          "keywords": ["关键词1", "关键词2"]
        }
      ]
    }
  ]
}
```

## 依赖库

```bash
pip install python-docx openpyxl pandas chardet
```

## 故障排除

### 路径错误

如果脚本找不到文件，检查 `scripts/*.py` 中的路径配置：

```python
# 默认使用最新的实验目录
EXPERIMENT_DIR = BASE_DIR / "assignments" / "2026-春季" / "汽服2302B班" / "07-car-gear"
```

如有需要，可以修改为其他实验目录。

### 编码问题

处理中文Word文档时可能出现编码问题，脚本会自动尝试处理常见编码。
