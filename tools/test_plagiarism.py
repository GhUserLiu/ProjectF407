# -*- coding: utf-8 -*-
"""
查重系统综合测试
Plagiarism Detection System Test

测试所有核心功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def print_section(title: str):
    """打印测试分节标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def test_imports():
    """测试模块导入"""
    print_section("1. 测试模块导入")

    tests = []

    # 核心模块
    try:
        from tools.plagiarism.core import PlagiarismDetector, SimilarityMethod
        print("✓ tools.plagiarism.core")
        tests.append(True)
    except Exception as e:
        print(f"✗ tools.plagiarism.core: {e}")
        tests.append(False)

    # 算法模块
    try:
        from tools.plagiarism.algorithms import sequence_similarity, cosine_similarity
        print("✓ tools.plagiarism.algorithms")
        tests.append(True)
    except Exception as e:
        print(f"✗ tools.plagiarism.algorithms: {e}")
        tests.append(False)

    # 配置模块
    try:
        from tools.plagiarism.config import PlagiarismConfig, default_config
        print("✓ tools.plagiarism.config")
        tests.append(True)
    except Exception as e:
        print(f"✗ tools.plagiarism.config: {e}")
        tests.append(False)

    # 语义检测模块
    try:
        from tools.plagiarism.semantic import SemanticDetector, SemanticMethod
        print("✓ tools.plagiarism.semantic")
        tests.append(True)
    except Exception as e:
        print(f"✗ tools.plagiarism.semantic: {e}")
        tests.append(False)

    # jieba分词（可选）
    try:
        import jieba
        print("✓ jieba (中文分词)")
    except ImportError:
        print("⚠ jieba 未安装 (可选，建议安装以提升准确度)")

    # sentence-transformers（可选）
    try:
        from sentence_transformers import SentenceTransformer
        print("✓ sentence-transformers (语义检测)")
    except ImportError:
        print("⚠ sentence-transformers 未安装 (可选，用于增强改写检测)")

    return all(tests)


def test_basic_similarity():
    """测试基础相似度计算"""
    print_section("2. 测试基础相似度计算")

    from tools.plagiarism.algorithms import (
        sequence_similarity,
        cosine_similarity,
        jaccard_similarity,
        hybrid_similarity
    )

    # 测试数据
    text1 = "这是一个测试文本，用于检测相似度算法是否正常工作。"
    text2 = "这是一个测试文本，用于检测相似度算法是否正常运行。"
    text3 = "完全不同的内容，用于测试低相似度情况。"

    tests = []

    # 测试序列相似度
    sim1 = sequence_similarity(text1, text2)
    sim2 = sequence_similarity(text1, text3)
    print(f"序列相似度: 相似文本={sim1:.1f}%, 不同文本={sim2:.1f}%")
    tests.append(sim1 > 80 and sim2 < 50)

    # 测试余弦相似度
    cos1 = cosine_similarity(text1, text2)
    cos2 = cosine_similarity(text1, text3)
    print(f"余弦相似度: 相似文本={cos1:.1f}%, 不同文本={cos2:.1f}%")
    tests.append(cos1 > 80 and cos2 < 50)

    # 测试混合相似度
    hyb1 = hybrid_similarity(text1, text2)
    hyb2 = hybrid_similarity(text1, text3)
    print(f"混合相似度: 相似文本={hyb1:.1f}%, 不同文本={hyb2:.1f}%")
    tests.append(hyb1 > 80 and hyb2 < 50)

    # 测试精确复制
    copy_sim = sequence_similarity(text1, text1)
    print(f"精确复制: {copy_sim:.1f}%")
    tests.append(copy_sim >= 99)

    if all(tests):
        print("✓ 基础相似度计算正常")
    else:
        print("✗ 基础相似度计算异常")

    return all(tests)


def test_paraphrase_detection():
    """测试改写检测"""
    print_section("3. 测试改写检测")

    try:
        from tools.plagiarism.semantic import SemanticDetector, SemanticMethod

        # 测试数据：原文和改写
        original = "通过按键控制LED灯的亮灭，实现转向灯功能。"
        paraphrase = "使用按键来控制LED灯光，从而完成转向灯的功能。"
        different = "这是一个完全不相关的句子内容。"

        # 使用TF-IDF方法
        detector = SemanticDetector(method=SemanticMethod.TFIDF, threshold=0.6)

        result1 = detector.detect(original, paraphrase)
        result2 = detector.detect(original, different)

        print(f"原文 vs 改写: 相似度={result1.similarity:.1f}%, 是改写={result1.is_paraphrase}")
        print(f"原文 vs 不同: 相似度={result2.similarity:.1f}%, 是改写={result2.is_paraphrase}")

        # 判断结果合理性
        tests = [
            result1.similarity > 50,  # 改写应该有一定相似度
            result2.similarity < 40,  # 不同文本相似度应该低
        ]

        if all(tests):
            print("✓ 改写检测正常")
        else:
            print("✗ 改写检测异常")

        return all(tests)

    except Exception as e:
        print(f"✗ 改写检测出错: {e}")
        return False


def test_code_similarity():
    """测试代码相似度检测"""
    print_section("4. 测试代码相似度检测")

    from tools.plagiarism.algorithms import sequence_similarity

    # 测试代码
    code1 = """
void main(void) {
    HAL_Init();
    while(1) {
        HAL_GPIO_WritePin(GPIOF, GPIO_PIN_9, GPIO_PIN_SET);
        HAL_Delay(500);
    }
}
"""

    code2 = """
void main(void) {
    HAL_Init();
    while(1) {
        HAL_GPIO_WritePin(GPIOF, GPIO_PIN_9, GPIO_PIN_RESET);
        HAL_Delay(500);
    }
}
"""

    code3 = """
int main() {
    printf("Hello World\\n");
    return 0;
}
"""

    tests = []

    # 测试相似代码
    sim1 = sequence_similarity(code1, code2)
    print(f"相似代码: {sim1:.1f}%")
    tests.append(sim1 > 70)

    # 测试不同代码
    sim2 = sequence_similarity(code1, code3)
    print(f"不同代码: {sim2:.1f}%")
    tests.append(sim2 < 50)

    if all(tests):
        print("✓ 代码相似度检测正常")
    else:
        print("✗ 代码相似度检测异常")

    return all(tests)


def test_plagiarism_detector():
    """测试完整查重检测器"""
    print_section("5. 测试完整查重检测器")

    try:
        from tools.plagiarism.core import PlagiarismDetector, SimilarityMethod
        from tools.plagiarism.config import PlagiarismConfig

        # 模拟提交数据
        submissions = {
            '2023001': {
                'name': '张三',
                'text': '通过按键控制LED灯的亮灭，实现转向灯功能。'
                       '程序使用HAL库进行GPIO配置，通过按键扫描获取状态，'
                       '然后根据状态控制LED灯闪烁。'
            },
            '2023002': {
                'name': '李四',
                'text': '通过按键来控制LED灯光，从而完成转向灯的功能。'
                       '代码采用HAL库实现GPIO初始化，利用按键检测逻辑获取输入，'
                       '随后根据按键状态控制LED灯的闪烁显示。'
            },
            '2023003': {
                'name': '王五',
                'text': '本实验主要学习了STM32F407的基本使用方法，'
                       '包括GPIO配置、定时器使用等基础内容。'
            }
        }

        # 小组信息
        group_info = {
            '2023001': '1组',
            '2023002': '2组',  # 不同组
            '2023003': '3组'
        }

        # 创建检测器（使用新配置系统）
        config = PlagiarismConfig(
            group_info=group_info,
            features=type('F', (), {
                'enable_semantic_detection': True,
                'enable_jieba': True
            })()
        )

        detector = PlagiarismDetector(
            method=SimilarityMethod.HYBRID,
            threshold=60.0,
            config=config
        )

        # 执行检测
        all_results, suspicious = detector.detect(submissions)

        print(f"检测完成: 可疑对数={len(suspicious)}")

        # 显示结果
        for result in suspicious:
            print(f"  {result.student_id} ↔ {result.similar_to}: "
                  f"{result.overall_similarity:.1f}% "
                  f"({'跨组' if result.is_cross_group else '同组'})")

            if result.semantic_similarity > 0:
                print(f"    语义相似度: {result.semantic_similarity:.1f}%")
            if result.is_paraphrase:
                print(f"    ⚠ 检测到改写")

        tests = [
            len(all_results) > 0,  # 应该有检测结果
            len(suspicious) >= 1,   # 应该有可疑对
        ]

        if all(tests):
            print("✓ 完整查重检测器正常")
        else:
            print("✗ 完整查重检测器异常")

        return all(tests)

    except Exception as e:
        print(f"✗ 完整查重检测出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_system():
    """测试配置系统"""
    print_section("6. 测试配置系统")

    try:
        from tools.plagiarism.config import PlagiarismConfig, SimilarityWeights

        # 测试默认配置
        config = PlagiarismConfig()
        print(f"默认权重: text={config.weights.text}, code={config.weights.code}")

        # 测试自定义配置
        custom = PlagiarismConfig(
            weights=SimilarityWeights(text=0.4, code=0.4, structure=0.1, semantic=0.1)
        )
        print(f"自定义权重: text={custom.weights.text}, code={custom.weights.code}")

        # 测试验证
        is_valid = custom.validate()
        print(f"配置验证: {'✓ 通过' if is_valid else '✗ 失败'}")

        # 测试标准化
        invalid = PlagiarismConfig(
            weights=SimilarityWeights(text=0.8, code=0.5)  # 总和>1
        )
        normalized = invalid.normalize()
        print(f"标准化前总和: {invalid.weights.text + invalid.weights.code:.2f}")
        print(f"标准化后总和: {normalized.weights.text + normalized.weights.code:.2f}")

        tests = [is_valid, abs((normalized.weights.text + normalized.weights.code) - 1.0) < 0.01]

        if all(tests):
            print("✓ 配置系统正常")
        else:
            print("✗ 配置系统异常")

        return all(tests)

    except Exception as e:
        print(f"✗ 配置系统出错: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print(" 查重系统功能测试 v2.4.0")
    print("=" * 60)

    results = []

    # 1. 模块导入测试
    results.append(("模块导入", test_imports()))

    # 2. 基础相似度测试
    results.append(("基础相似度", test_basic_similarity()))

    # 3. 改写检测测试
    results.append(("改写检测", test_paraphrase_detection()))

    # 4. 代码相似度测试
    results.append(("代码相似度", test_code_similarity()))

    # 5. 完整检测器测试
    results.append(("完整检测器", test_plagiarism_detector()))

    # 6. 配置系统测试
    results.append(("配置系统", test_config_system()))

    # 汇总结果
    print_section("测试结果汇总")

    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 通过")

    if passed_count == total_count:
        print("🎉 所有测试通过！查重系统运行正常。")
        return 0
    else:
        print("⚠ 部分测试失败，请检查相关功能。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
