"""
STM32教学管理系统 - 测试数据生成脚本

优先使用真实学生数据生成测试包
"""
import os
import shutil
import zipfile
from pathlib import Path

# 项目路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
GUI_APP_DIR = Path(__file__).parent
TEST_DATA_DIR = GUI_APP_DIR / "test_data"
TEMPLATE_DIR = PROJECT_ROOT / "docs" / "teaching" / "common" / "templates"

# 真实数据来源
REAL_DATA_DIR_B = PROJECT_ROOT / "docs" / "teaching" / "2026-春季" / "汽服2302B班" / "07-car-gear"
REAL_PROCESSED_DIR_B = REAL_DATA_DIR_B / "processed"

# 2301B班真实数据
REAL_DATA_DIR_A = PROJECT_ROOT / "docs" / "teaching" / "2026-春季" / "汽服2301B班" / "07-car-gear"
REAL_EXTRACTED_DIR_A = REAL_DATA_DIR_A / "submissions" / "extracted"

# teaching_demo 目录（用于多班级测试数据）
TEACHING_DEMO_DIR = TEST_DATA_DIR / "teaching_demo" / "2026-春季"

# 真实学生数据（从2026春季汽服2302B班）
REAL_STUDENTS_CLASS_B = [
    ("23071140229", "田浩然"),
    ("23071140230", "冀虹鑫"),
    ("23071140232", "王浩炜"),
    ("23071140234", "杜慧君"),
    ("23071140235", "郑子健"),
    ("23071140238", "孟祥祖"),
    ("23071140239", "牛煜哲"),
]

# 真实学生数据（汽服2301B班 - 从extracted目录获取）
REAL_STUDENTS_CLASS_A = [
    ("23071140123", "学生A"),
    ("23071140125", "学生B"),
    ("23071140128", "学生C"),
    ("23071140129", "学生D"),
    ("23071140135", "学生E"),
    ("23071140136", "学生F"),
    ("23071140141", "学生G"),
]

# 模拟学生数据（用于测试更多学生）
MOCK_STUDENTS_CLASS_A = [
    ("23071140101", "张伟"),
    ("23071140102", "李娜"),
    ("23071140103", "王强"),
    ("23071140104", "赵敏"),
    ("23071140105", "刘洋"),
    ("23071140106", "陈静"),
    ("23071140107", "杨帆"),
    ("23071140108", "黄磊"),
]

# 真实学生数据（汽服2302B班 - 额外学生）
REAL_STUDENTS_CLASS_B_EXTRA = [
    ("23071140201", "董雨航"),
    ("23071140202", "陈乐莹"),
    ("23071140205", "任梦泱"),
    ("23071140210", "王倩倩"),
    ("23071140213", "吴延洁"),
]

# 示例代码模板
CODE_TEMPLATES = {
    "gear_experiment": """#include "stm32f4xx_hal.h"

/* 汽车档位模拟器 - 主程序 */

// 档位定义
typedef enum {
    GEAR_P = 0,  // 驻车档
    GEAR_R = 1,  // 倒车档
    GEAR_N = 2,  // 空档
    GEAR_D = 3   // 前进档
} GearType;

GearType current_gear = GEAR_P;

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    while (1)
    {
        // 读取按键状态
        // 更新档位
        // 显示档位
    }
}
""",
}

# 学生名单 CSV 格式（从真实数据生成）
def create_student_list_csv():
    """创建两个班级的学生名单CSV"""
    # 创建汽服2302B班学生名单（分组为1-3）
    csv_content_b = "学号,姓名,班级,分组\n"
    for i, (student_id, name) in enumerate(REAL_STUDENTS_CLASS_B + REAL_STUDENTS_CLASS_B_EXTRA):
        group = (i % 3) + 1  # 分组循环：1,2,3
        csv_content_b += f"{student_id},{name},汽服2302B班,{group}\n"

    class_dir_b = TEACHING_DEMO_DIR / "汽服2302B班"
    class_dir_b.mkdir(parents=True, exist_ok=True)
    csv_file_b = class_dir_b / "汽服2302B班_学生名单.csv"
    csv_file_b.write_text(csv_content_b, encoding="utf-8-sig")
    print(f"[创建] 学生名单: {csv_file_b.relative_to(TEST_DATA_DIR)} ({len(REAL_STUDENTS_CLASS_B) + len(REAL_STUDENTS_CLASS_B_EXTRA)}人)")

    # 创建汽服2301B班学生名单（分组为1-2）- 使用真实学号
    csv_content_a = "学号,姓名,班级,分组\n"
    for i, (student_id, name) in enumerate(REAL_STUDENTS_CLASS_A):
        group = (i % 2) + 1  # 分组循环：1,2
        csv_content_a += f"{student_id},{name},汽服2301B班,{group}\n"

    class_dir_a = TEACHING_DEMO_DIR / "汽服2301B班"
    class_dir_a.mkdir(parents=True, exist_ok=True)
    csv_file_a = class_dir_a / "汽服2301B班_学生名单.csv"
    csv_file_a.write_text(csv_content_a, encoding="utf-8-sig")
    print(f"[创建] 学生名单: {csv_file_a.relative_to(TEST_DATA_DIR)} ({len(REAL_STUDENTS_CLASS_A)}人)")


def copy_real_submissions():
    """从真实数据复制学生提交到 teaching_demo 目录结构（汽服2302B班）"""
    # 创建班级目录结构: teaching_demo/2026-春季/汽服2302B班/07-car-gear/submissions/
    submissions_dir = TEACHING_DEMO_DIR / "汽服2302B班" / "07-car-gear" / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    all_students = REAL_STUDENTS_CLASS_B + REAL_STUDENTS_CLASS_B_EXTRA
    for student_id, name in all_students:
        student_dir = REAL_PROCESSED_DIR_B / student_id
        if not student_dir.exists():
            continue

        # 查找docx文件作为提交文件
        docx_files = list(student_dir.glob("*.docx"))
        if not docx_files:
            # 如果没有docx，尝试doc
            doc_files = list(student_dir.glob("*.doc"))
            if doc_files:
                docx_files = doc_files

        if not docx_files:
            continue

        # 创建ZIP文件
        zip_name = f"{student_id}_{name}_汽车档位模拟器.zip"
        zip_path = submissions_dir / zip_name

        # 检查是否已存在
        if zip_path.exists():
            continue

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加报告文件
            for doc_file in docx_files:
                zipf.write(doc_file, doc_file.name)

            # 添加代码文件
            code_content = CODE_TEMPLATES.get("gear_experiment", "")
            zipf.writestr("main.c", code_content)

        print(f"[复制] 真实提交: {zip_path.relative_to(TEST_DATA_DIR)}")
        copied += 1

    print(f"[完成] 汽服2302B班: 复制了 {copied} 份真实提交")
    return copied


def create_class_a_submissions():
    """复制汽服2301B班的真实提交"""
    submissions_dir = TEACHING_DEMO_DIR / "汽服2301B班" / "07-car-gear" / "submissions"
    submissions_dir.mkdir(parents=True, exist_ok=True)

    copied = 0

    # 从真实数据目录复制ZIP文件
    if REAL_EXTRACTED_DIR_A.exists():
        for zip_file in REAL_EXTRACTED_DIR_A.glob("*.zip"):
            # 提取学号
            student_id = zip_file.stem  # 文件名去掉.zip后缀就是学号

            # 从REAL_STUDENTS_CLASS_A中获取姓名
            name = "未知"
            for sid, sname in REAL_STUDENTS_CLASS_A:
                if sid == student_id:
                    name = sname
                    break

            # 目标路径
            target_zip = submissions_dir / f"{student_id}_{name}_汽车档位模拟器.zip"

            # 复制文件
            if not target_zip.exists():
                shutil.copy(zip_file, target_zip)
                print(f"[复制] 汽服2301B班真实提交: {target_zip.relative_to(TEST_DATA_DIR)}")
                copied += 1

    print(f"[完成] 汽服2301B班: 复制了 {copied} 份真实提交")
    return copied


def create_additional_submissions():
    """补充汽服2302B班的模拟提交（当真实数据不够时）"""
    submissions_dir = TEACHING_DEMO_DIR / "汽服2302B班" / "07-car-gear" / "submissions"

    # 检查当前数量
    current_count = len(list(submissions_dir.glob("*.zip")))
    needed = max(0, 6 - current_count)  # 目标至少6个

    if needed == 0:
        return 0

    print(f"[补充] 汽服2302B班需要 {needed} 个模拟提交")

    additional_students = [
        ("23071140220", "张明"),
        ("23071140221", "李华"),
        ("23071140222", "王强"),
        ("23071140223", "赵敏"),
        ("23071140224", "刘洋"),
    ]

    count = 0
    for student_id, name in additional_students[:needed]:
        # 创建ZIP文件
        zip_name = f"{student_id}_{name}_汽车档位模拟器.zip"
        zip_path = submissions_dir / zip_name

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加代码文件
            code_content = CODE_TEMPLATES.get("gear_experiment", "")
            zipf.writestr("main.c", code_content)

            # 如果模板存在，添加模板
            template_file = TEMPLATE_DIR / "实验报告模板.docx"
            if template_file.exists():
                zipf.write(template_file, "实验报告.docx")

        print(f"[创建] 汽服2302B班模拟提交: {zip_path.relative_to(TEST_DATA_DIR)}")
        count += 1

    print(f"[完成] 汽服2302B班: 创建了 {count} 个模拟提交")
    return count


def create_rubric_examples():
    """创建评分标准示例"""
    rubrics_dir = TEST_DATA_DIR / "rubrics"
    rubrics_dir.mkdir(parents=True, exist_ok=True)

    # 从项目复制评分标准
    source_rubric = PROJECT_ROOT / "docs" / "teaching" / "common" / "rubrics"
    if source_rubric.exists():
        for json_file in source_rubric.glob("*.json"):
            shutil.copy(json_file, rubrics_dir / json_file.name)
            print(f"[复制] 评分标准: {json_file.name}")


def create_template_examples():
    """创建模板文件示例"""
    templates_dir = TEST_DATA_DIR / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)

    # 从项目复制模板
    if TEMPLATE_DIR.exists():
        for template_file in TEMPLATE_DIR.glob("*.docx"):
            shutil.copy(template_file, templates_dir / template_file.name)
            print(f"[复制] 模板: {template_file.name}")
        for md_file in TEMPLATE_DIR.glob("*.md"):
            shutil.copy(md_file, templates_dir / md_file.name)
            print(f"[复制] 模板: {md_file.name}")


def create_example_results():
    """创建示例处理结果"""
    results_dir = TEST_DATA_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    readme = """测试数据 - 处理结果目录

此目录用于存放系统处理后的示例结果，包括：
- 查重检测报告
- 自动评分结果
- 学生反馈文档
- 成绩统计表

运行系统后，处理结果将保存在这里。
"""
    (results_dir / "README.txt").write_text(readme, encoding="utf-8")
    print(f"[创建] 结果目录说明")


def main():
    """生成所有测试数据"""
    print("STM32教学管理系统 - 测试数据生成（使用真实数据）")
    print("=" * 60)

    # 清理旧数据
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR)
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 创建基础目录结构（用于单项目测试）
    (TEST_DATA_DIR / "students").mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "submissions").mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "templates").mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "rubrics").mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "results").mkdir(parents=True, exist_ok=True)

    # 创建 teaching_demo 目录结构（用于多班级测试）
    # teaching_demo/2026-春季/汽服2302B班/07-car-gear/submissions/
    TEACHING_DEMO_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 创建学生名单
    print("\n[1/8] 创建学生名单...")
    create_student_list_csv()

    # 2. 创建汽服2301B班提交
    print("\n[2/8] 创建汽服2301B班学生提交...")
    class_a_count = create_class_a_submissions()

    # 3. 复制汽服2302B班真实提交
    print("\n[3/8] 复制汽服2302B班真实学生提交...")
    real_count = copy_real_submissions()

    # 4. 补充汽服2302B班模拟提交（如果需要）
    if real_count < 6:
        print("\n[4/8] 补充汽服2302B班模拟提交...")
        additional_count = create_additional_submissions()
    else:
        print("\n[4/8] 跳过补充（汽服2302B班已有足够数据）")
        additional_count = 0

    # 5. 创建评分标准示例
    print("\n[5/8] 创建评分标准...")
    create_rubric_examples()

    # 6. 创建模板示例
    print("\n[6/8] 创建模板文件...")
    create_template_examples()

    # 7. 创建结果目录说明
    print("\n[7/8] 创建结果目录...")
    create_example_results()

    # 8. 创建 teaching_demo 目录结构说明
    print("\n[8/8] 创建 teaching_demo 目录说明...")
    teaching_readme = """测试数据 - 多班级教学演示目录

此目录包含完整的教学场景数据，用于测试多班级、查重检测、评分评估等功能。

目录结构：
teaching_demo/
└── 2026-春季/
    ├── 汽服2301B班/
    │   ├── 汽服2301B班_学生名单.csv
    │   └── 07-car-gear/
    │       └── submissions/      # 学生提交文件（8个）
    └── 汽服2302B班/
        ├── 汽服2302B班_学生名单.csv
        └── 07-car-gear/
            └── submissions/      # 学生提交文件（真实+模拟）

使用方式：
1. 多班级视图：选择基础目录为 teaching_demo，系统自动发现班级
2. 查重检测：选择 2026-春季/汽服2302B班/07-car-gear/submissions 目录
3. 评分评估：配合学生名单使用 submissions 目录

数据来源：
- 真实教学场景（2026春季学期）
- 部分学生信息已脱敏处理
- 汽服2302B班使用真实提交，汽服2301B班使用模拟提交
"""
    teaching_readme_file = TEACHING_DEMO_DIR / "README.txt"
    teaching_readme_file.write_text(teaching_readme, encoding="utf-8")
    print(f"[创建] {teaching_readme_file.relative_to(TEST_DATA_DIR)}")

    # 创建总说明
    readme = f"""STM32教学管理系统 - 测试数据目录

此目录包含来自真实教学场景的测试数据。

数据来源：
- 班级：汽服2302B班、汽服2301B班
- 学期：2025-2026学年 第二学期
- 实验：汽车档位模拟器

目录结构：
├── students/           # 学生名单（传统格式）
├── submissions/        # 学生提交（传统格式）
├── templates/          # 报告模板（DOCX格式）
├── rubrics/            # 评分标准（JSON格式）
├── results/            # 处理结果输出（运行后生成）
└── teaching_demo/      # 多班级教学演示数据
    └── 2026-春季/
        ├── 汽服2301B班/ (8个学生)
        └── 汽服2302B班/ (12个学生)

测试说明：
- 学生提交来自2026春季学期的真实作业
- 部分学生信息已脱敏处理
- 可用于测试查重、评分等全部功能
- teaching_demo 目录用于测试多班级功能
"""
    (TEST_DATA_DIR / "README.txt").write_text(readme, encoding="utf-8")

    # 统计
    class_a_student_count = len(MOCK_STUDENTS_CLASS_A)
    class_b_student_count = len(REAL_STUDENTS_CLASS_B) + len(REAL_STUDENTS_CLASS_B_EXTRA)
    class_a_submissions = len(list((TEACHING_DEMO_DIR / "汽服2301B班" / "07-car-gear" / "submissions").glob("*.zip")))
    class_b_submissions = len(list((TEACHING_DEMO_DIR / "汽服2302B班" / "07-car-gear" / "submissions").glob("*.zip")))

    print(f"\n[OK] 测试数据生成完成!")
    print(f"  位置: {TEST_DATA_DIR}")
    print(f"  多班级目录: teaching_demo/2026-春季/")
    print(f"  汽服2301B班: {class_a_student_count} 学生, {class_a_submissions} 提交")
    print(f"  汽服2302B班: {class_b_student_count} 学生, {class_b_submissions} 提交")
    print(f"  数据来源: 真实教学场景 + 模拟数据")


if __name__ == "__main__":
    main()
