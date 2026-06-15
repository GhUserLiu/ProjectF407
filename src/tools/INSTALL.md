# 查重系统安装指南

## 快速安装

### 安装所有依赖
```bash
pip install -r requirements.txt
```

### 分步安装

#### 1. 核心依赖（必需）
```bash
pip install python-docx openpyxl
```

#### 2. 中文分词（强烈推荐）
```bash
pip install jieba
```

#### 3. 语义检测（可选，增强改写检测）
```bash
pip install sentence-transformers
```
> 注意：首次运行会下载约100MB的模型文件

#### 4. 图片处理（可选）
```bash
pip install Pillow
```

## 功能对应依赖

| 功能 | 依赖项 | 必需性 |
|------|--------|--------|
| Word文档读取 | python-docx | ✅ 必需 |
| Excel报告生成 | openpyxl | ✅ 必需 |
| 中文精确分词 | jieba | ⭐ 强烈推荐 |
| 改写检测 | sentence-transformers | ⚠️ 可选 |
| 图片相似度 | Pillow | ⚠️ 可选 |

## 验证安装

```bash
# 检查核心依赖
python -c "import docx; print('python-docx OK')"
python -c "import openpyxl; print('openpyxl OK')"

# 检查可选依赖
python -c "import jieba; print('jieba OK')" 2>nul
python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')" 2>nul
python -c "from PIL import Image; print('Pillow OK')" 2>nul
```

## 常见问题

### Q1: jieba 安装失败
```bash
# 使用国内镜像
pip install jieba -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: sentence-transformers 安装慢
```bash
# 使用国内镜像
pip install sentence-transformers -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q3: 模型下载失败
首次运行时，模型会自动下载。如失败，可手动下载：
```bash
# 设置镜像（可选）
export HF_ENDPOINT=https://hf-mirror.com
```
