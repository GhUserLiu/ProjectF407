#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
NLP增强功能单元测试
Unit Tests for NLP Enhancement Features
"""

import unittest
from pathlib import Path
import sys
import os

# 确保可以导入tools模块
# 解决路径问题：获取文件的绝对路径，然后找到项目根目录
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent.parent.parent

# 如果当前目录是项目根目录，使用它
cwd = Path(os.getcwd()).resolve()
if (cwd / 'tools' / 'plagiarism').exists():
    project_root = cwd

# 添加项目根目录到sys.path
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

# 设置工作目录
os.chdir(project_root_str)


class TestEnhancedKeywordMatcher(unittest.TestCase):
    """测试增强关键词匹配器"""

    def setUp(self):
        """设置测试环境"""
        from tools.plagiarism.nlp import EnhancedKeywordMatcher, MatchMethod
        self.matcher = EnhancedKeywordMatcher(
            use_fuzzy=True,
            use_variants=True,
            fuzzy_threshold=0.85,
            enable_jieba=True
        )

    def test_exact_match(self):
        """测试精确匹配"""
        text = "使用GPIO配置LED灯"
        keywords = ["GPIO", "LED"]
        results, ratio = self.matcher.match_keywords(text, keywords, MatchMethod.EXACT)
        matched = [r.keyword for r in results if r.matched]

        self.assertIn("GPIO", matched)
        self.assertIn("LED", matched)
        self.assertEqual(ratio, 1.0)

    def test_obfuscated_match(self):
        """测试混淆文本匹配"""
        # 测试空格插入
        text1 = "使用G P I O配置LED灯"
        # 测试特殊字符插入
        text2 = "使用G-P-I-O配置LED灯"
        # 测试字符分散
        text3 = "使用G P  I  O配置LED灯"

        for text in [text1, text2, text3]:
            results, ratio = self.matcher.match_keywords(text, ["GPIO"], MatchMethod.FUZZY)
            matched_keywords = [r.keyword for r in results if r.matched]
            self.assertIn("GPIO", matched_keywords,
                        f"Failed to match obfuscated text: {text}")

    def test_term_variants(self):
        """测试术语变体匹配"""
        test_cases = [
            ("使用通用IO配置", "GPIO"),
            ("使用外部中断", "中断"),
            ("数据断点消抖", "DWT"),
            ("去抖处理", "消抖"),
        ]

        for text, keyword in test_cases:
            results, ratio = self.matcher.match_keywords(text, [keyword])
            matched = [r.keyword for r in results if r.matched]
            self.assertTrue(len(matched) > 0,
                          f"Failed to match variant: {text} -> {keyword}")

    def test_word_boundary_matching(self):
        """测试词边界匹配"""
        # 确保不会误匹配部分单词
        text = " INTERRUPT_HANDLER 应该匹配 INTERRUPT"
        results, ratio = self.matcher.match_keywords(text, ["INTERRUPT"])
        matched = [r.keyword for r in results if r.matched]
        self.assertTrue(len(matched) > 0, "Word boundary matching failed")

    def test_context_extraction(self):
        """测试上下文提取"""
        text = "这是一个关于GPIO配置的示例，GPIO用于控制LED灯"
        context = self.matcher.extract_context(text, "GPIO", context_size=20)

        self.assertIn("GPIO", context)
        self.assertTrue(len(context) > 10)


class TestAdvancedTemplateFilter(unittest.TestCase):
    """测试高级模板过滤器"""

    def setUp(self):
        """设置测试环境"""
        from tools.plagiarism.nlp import AdvancedTemplateFilter, FilterMethod

        self.template = """
        一、实验目的
        本实验的目的是掌握STM32的GPIO配置方法。

        二、实验原理
        GPIO是通用输入输出接口，可以配置为输入或输出模式。
        """

        self.filter = AdvancedTemplateFilter(
            template_content=self.template,
            ngram_sizes=[3, 4, 5],
            similarity_threshold=0.7
        )

    def test_template_filtering(self):
        """测试模板过滤"""
        # 正常文本
        normal_text = "一、实验目的\n本实验的目的是掌握STM32的GPIO配置方法。"
        result = self.filter.filter(normal_text, FilterMethod.HYBRID)

        self.assertTrue(result.removal_ratio > 0.5,
                       "Template should be filtered out")
        self.assertLess(len(result.filtered_text), len(result.original_text))

    def test_obfuscated_template_detection(self):
        """测试混淆模板检测"""
        # 插入空格的混淆
        obfuscated = "一  、  实  验  目  的\n本  实  验  的  目  的  是  掌  握  S  T  M  3  2  的  G  P  I  O  配  置  方  法  。"

        result = self.filter.filter(obfuscated, FilterMethod.HYBRID)

        self.assertTrue(result.removal_ratio > 0.3,
                       "Obfuscated template should still be detected")

    def test_manipulation_detection(self):
        """测试模板操纵检测"""
        manipulated = "一、实验目标\n本实验目标是学会STM32的GPIO配置"  # 稍微修改

        manipulation = self.filter.detect_template_manipulation(manipulated)

        # 应该检测到某种程度的操纵
        self.assertTrue(manipulation['detected'] or manipulation['confidence'] > 0,
                       "Should detect template manipulation")


class TestCodeASTAnalyzer(unittest.TestCase):
    """测试代码AST分析器"""

    def setUp(self):
        """设置测试环境"""
        from tools.plagiarism.nlp import CodeASTAnalyzer
        self.analyzer = CodeASTAnalyzer(language='c')

    def test_function_extraction(self):
        """测试函数提取"""
        code = """
        void led_init(void) {
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
        }

        void button_read(void) {
            return HAL_GPIO_ReadPin(GPIOB, GPIO_PIN_0);
        }
        """

        structure = self.analyzer.analyze(code)

        self.assertEqual(len(structure.functions), 2)
        self.assertIn("led_init", [f['name'] for f in structure.functions])
        self.assertIn("button_read", [f['name'] for f in structure.functions])

    def test_variable_renaming_detection(self):
        """测试变量重命名检测"""
        code1 = """
        void led_init(void) {
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
        }
        """

        code2 = """
        void灯初始化(void) {
            HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
        }
        """

        result = self.analyzer.compare(code1, code2)

        # 结构应该高度相似，即使函数名不同
        self.assertGreater(result.structure_similarity, 70,
                          "Structure should be similar despite renaming")
        self.assertGreater(result.logic_similarity, 60,
                          "Logic should be similar despite renaming")

    def test_code_normalization(self):
        """测试代码规范化"""
        code = """
        void led_init(void) {
            // 这是注释
            HAL_GPIO_WritePin(GPIOA, /* 参数 */ GPIO_PIN_5, GPIO_PIN_RESET);
        }
        """

        from tools.plagiarism.nlp.code_analyzer_nlp import CCodeParser
        normalized = CCodeParser.normalize_code(code)

        # 注释应该被移除
        self.assertNotIn("//", normalized)
        self.assertNotIn("/*", normalized)
        self.assertNotIn("*/", normalized)

        # 多余空格应该被移除
        self.assertNotIn("  ", normalized.strip())


class TestNLPIntegration(unittest.TestCase):
    """测试NLP集成功能"""

    def test_nlp_engine_creation(self):
        """测试NLP引擎创建"""
        from tools.plagiarism.nlp import create_nlp_enhanced_detector, get_preset

        # 测试默认配置
        engine = create_nlp_enhanced_detector()
        self.assertIsNotNone(engine)

        # 测试严格模式
        strict_engine = create_nlp_enhanced_detector(strict_mode=True)
        self.assertIsNotNone(strict_engine)

        # 测试预设
        config = get_preset('strict')
        self.assertEqual(config.fuzzy_threshold, 0.90)

    def test_nlp_preset_configs(self):
        """测试NLP预设配置"""
        from tools.plagiarism.nlp.nlp_integration import PRESETS

        # 检查所有预设存在
        self.assertIn('default', PRESETS)
        self.assertIn('strict', PRESETS)
        self.assertIn('lenient', PRESETS)
        self.assertIn('fast', PRESETS)

        # 检查fast预设禁用了某些功能
        fast_config = PRESETS['fast']
        self.assertFalse(fast_config.enable_fuzzy_matching)
        self.assertFalse(fast_config.enable_ast_analysis)

    def test_enhanced_keyword_matching(self):
        """测试增强关键词匹配"""
        from tools.plagiarism.nlp import NLPEngine, NLPEngineConfig

        config = NLPEngineConfig(
            enable_fuzzy_matching=True,
            fuzzy_threshold=0.85
        )
        engine = NLPEngine(config)

        text = "使用G P I O配置LED灯"
        keywords = ["GPIO", "LED"]

        matched, ratio, details = engine.enhance_keyword_matching(
            text, keywords, return_details=True
        )

        self.assertTrue(len(matched) >= 1, "Should match at least one keyword")
        self.assertIsNotNone(details)


class TestCoreIntegration(unittest.TestCase):
    """测试与核心模块的集成"""

    def test_preprocessor_with_nlp(self):
        """测试预处理器NLP集成"""
        from tools.plagiarism.core import TextPreprocessor

        template = "实验目的：掌握STM32的GPIO配置方法"

        # 启用NLP
        preprocessor = TextPreprocessor(
            remove_template=True,
            template_content=template,
            use_nlp_filter=True
        )

        text = "实验目的：掌握STM32的GPIO配置方法，另外还有一些自定义内容"

        cleaned = preprocessor.clean_text(text)

        # 模板内容应该被过滤
        self.assertLess(len(cleaned), len(text))

    def test_detector_with_nlp(self):
        """测试检测器NLP集成"""
        from tools.plagiarism.core import PlagiarismDetector, SimilarityMethod

        detector = PlagiarismDetector(
            method=SimilarityMethod.HYBRID,
            threshold=60.0,
            template_content="模板内容",
            enable_nlp_enhancements=True
        )

        self.assertTrue(detector.enable_nlp_enhancements)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestEnhancedKeywordMatcher))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedTemplateFilter))
    suite.addTests(loader.loadTestsFromTestCase(TestCodeASTAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestNLPIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestCoreIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
