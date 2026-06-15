"""
测试模块导入
"""
import sys
from pathlib import Path

print("=== 测试模块导入 ===")

# 测试基础模块
print("1. 测试 PyQt6...")
try:
    from PyQt6.QtWidgets import QApplication
    print("   [OK] PyQt6")
except Exception as e:
    print(f"   [ERROR] PyQt6: {e}")

# 测试 tools 模块
print("2. 测试 tools.security...")
try:
    from tools.security import path_validator
    print("   [OK] tools.security")
except Exception as e:
    print(f"   [ERROR] tools.security: {e}")

print("3. 测试 tools.submission_utils...")
try:
    import tools.submission_utils
    print("   [OK] tools.submission_utils")
except Exception as e:
    print(f"   [ERROR] tools.submission_utils: {e}")

print("4. 测试 tools.plagiarism...")
try:
    from tools.plagiarism.core.multi_class_detector import create_multi_class_config
    print("   [OK] tools.plagiarism")
except Exception as e:
    print(f"   [ERROR] tools.plagiarism: {e}")

# 测试 app 模块
print("5. 测试 app.models...")
try:
    from app.models.domain import MultiClassProjectConfig
    print("   [OK] app.models")
except Exception as e:
    print(f"   [ERROR] app.models: {e}")

print("6. 测试 app.core.multi_class_service...")
try:
    from app.core.multi_class_service import MultiClassService
    print("   [OK] app.core.multi_class_service")
except Exception as e:
    print(f"   [ERROR] app.core.multi_class_service: {e}")

print("=== 完成 ===")
input("按 Enter 退出...")
