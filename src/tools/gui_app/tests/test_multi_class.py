"""
多班级视图和功能测试

测试多班级处理服务的核心功能
"""

import sys
import unittest
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 添加gui_app目录到路径
gui_app_root = Path(__file__).parents[1]
if str(gui_app_root) not in sys.path:
    sys.path.insert(0, str(gui_app_root))


class TestMultiClassModels(unittest.TestCase):
    """测试多班级数据模型"""

    def test_experiment_type_enum(self):
        """测试实验类型枚举"""
        from tools.gui_app.app.models.domain import ExperimentType

        self.assertEqual(ExperimentType.CAR_GEAR.value, "档位实验")
        self.assertEqual(ExperimentType.TURN_SIGNAL.value, "转向灯实验")

    def test_class_config_model(self):
        """测试ClassConfig模型"""
        from tools.gui_app.app.models.domain import ClassConfig, ExperimentType

        config = ClassConfig(
            class_id="test_01b",
            class_name="测试1B班",
            experiment_dir=Path("/test/path"),
            experiment_type=ExperimentType.CAR_GEAR
        )

        self.assertEqual(config.class_id, "test_01b")
        self.assertEqual(config.class_name, "测试1B班")
        self.assertEqual(config.student_count, 0)  # 默认值

    def test_class_config_to_dict(self):
        """测试ClassConfig序列化"""
        from tools.gui_app.app.models.domain import ClassConfig, ExperimentType

        config = ClassConfig(
            class_id="test_01b",
            class_name="测试1B班",
            experiment_dir=Path("/test/path"),
            experiment_type=ExperimentType.CAR_GEAR,
            student_count=30,
            submission_count=28,
            avg_score=85.5
        )

        data = config.to_dict()

        self.assertEqual(data['class_id'], "test_01b")
        self.assertEqual(data['student_count'], 30)
        self.assertEqual(data['submission_count'], 28)
        self.assertAlmostEqual(data['avg_score'], 85.5)

    def test_class_config_from_dict(self):
        """测试ClassConfig反序列化"""
        from tools.gui_app.app.models.domain import ClassConfig

        data = {
            'class_id': 'test_02b',
            'class_name': '测试2B班',
            'experiment_dir': '/test/path2',
            'experiment_type': '档位实验',  # 使用正确的枚举值
            'student_count': 25,
            'submission_count': 24,
            'avg_score': 88.0,
            'suspicious_rate': 5.0
        }

        config = ClassConfig.from_dict(data)

        self.assertEqual(config.class_id, 'test_02b')
        self.assertEqual(config.student_count, 25)
        self.assertAlmostEqual(config.suspicious_rate, 5.0)

    def test_multi_class_project_config(self):
        """测试MultiClassProjectConfig模型"""
        from tools.gui_app.app.models.domain import (
            MultiClassProjectConfig,
            ClassConfig,
            ExperimentType,
            SimilarityWeights
        )

        classes = [
            ClassConfig(
                class_id="class_1",
                class_name="班级1",
                experiment_dir=Path("/path1"),
                experiment_type=ExperimentType.CAR_GEAR
            ),
            ClassConfig(
                class_id="class_2",
                class_name="班级2",
                experiment_dir=Path("/path2"),
                experiment_type=ExperimentType.CAR_GEAR
            )
        ]

        config = MultiClassProjectConfig(
            project_id="proj_123",
            project_name="测试项目",
            classes=classes,
            shared_threshold=65.0,
            enable_cross_class_detection=True
        )

        self.assertEqual(config.project_id, "proj_123")
        self.assertEqual(len(config.classes), 2)
        self.assertEqual(config.shared_threshold, 65.0)
        self.assertTrue(config.enable_cross_class_detection)

    def test_multi_class_config_serialization(self):
        """测试MultiClassProjectConfig序列化"""
        from tools.gui_app.app.models.domain import (
            MultiClassProjectConfig,
            ClassConfig,
            ExperimentType
        )

        config = MultiClassProjectConfig(
            project_id="test_proj",
            project_name="测试多班级项目",
            classes=[
                ClassConfig(
                    class_id="c1",
                    class_name="班级1",
                    experiment_dir=Path("/p1"),
                    experiment_type=ExperimentType.CAR_GEAR
                )
            ],
            shared_threshold=70.0
        )

        # 序列化
        data = config.to_dict()
        self.assertEqual(data['project_id'], "test_proj")
        self.assertEqual(len(data['classes']), 1)

        # 反序列化
        restored = MultiClassProjectConfig.from_dict(data)
        self.assertEqual(restored.project_id, "test_proj")
        self.assertEqual(len(restored.classes), 1)
        self.assertEqual(restored.shared_threshold, 70.0)


class TestMultiClassFiles(unittest.TestCase):
    """测试多班级相关文件"""

    def test_multi_class_service_file_exists(self):
        """测试多班级服务文件存在"""
        service_path = project_root / "tools/gui_app/app/core/multi_class_service.py"
        self.assertTrue(service_path.exists(), f"Service file not found: {service_path}")

    def test_multi_class_view_file_exists(self):
        """测试多班级视图文件存在"""
        view_path = project_root / "tools/gui_app/app/ui/views/multi_class_view.py"
        self.assertTrue(view_path.exists(), f"View file not found: {view_path}")

    def test_multi_class_service_has_required_classes(self):
        """测试服务文件包含必需的类"""
        service_path = project_root / "tools/gui_app/app/core/multi_class_service.py"
        content = service_path.read_text(encoding='utf-8')

        self.assertIn('class MultiClassWorker', content)
        self.assertIn('class MultiClassService', content)

    def test_multi_class_view_has_required_methods(self):
        """测试视图包含必需的方法"""
        view_path = project_root / "tools/gui_app/app/ui/views/multi_class_view.py"
        content = view_path.read_text(encoding='utf-8')

        self.assertIn('def _create_config_section', content)
        self.assertIn('def _on_discover_classes', content)
        self.assertIn('def _on_start_detection', content)


class TestMainIntegration(unittest.TestCase):
    """测试主窗口集成"""

    def test_main_window_imports_multi_class(self):
        """测试主窗口导入多班级视图"""
        main_window_path = project_root / "tools/gui_app/app/ui/main_window.py"
        content = main_window_path.read_text(encoding='utf-8')

        self.assertIn('from app.ui.views.multi_class_view import MultiClassView', content)

    def test_main_window_has_multi_class_view_reference(self):
        """测试主窗口包含多班级视图引用"""
        main_window_path = project_root / "tools/gui_app/app/ui/main_window.py"
        content = main_window_path.read_text(encoding='utf-8')

        self.assertIn('self.multi_class_view = None', content)
        self.assertIn("self.multi_class_view = MultiClassView()", content)

    def test_main_window_registers_multi_class_view(self):
        """测试主窗口注册多班级视图"""
        main_window_path = project_root / "tools/gui_app/app/ui/main_window.py"
        content = main_window_path.read_text(encoding='utf-8')

        self.assertIn("register_view('multi_class'", content)

    def test_navigation_has_multi_class_item(self):
        """测试导航包含多班级选项"""
        main_window_path = project_root / "tools/gui_app/app/ui/main_window.py"
        content = main_window_path.read_text(encoding='utf-8')

        self.assertIn("'multi_class'", content)
        self.assertIn("多班级", content)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestMultiClassModels))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiClassFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestMainIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
