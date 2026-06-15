#!/usr/bin/env python3
"""
STM32 教学管理系统 - 发布打包脚本

自动构建和打包发布版本
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None):
    """运行命令"""
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=cwd)
    if result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        sys.exit(1)


def build_onefile(spec_dir, dist_dir):
    """构建单文件版本"""
    print("\n=== Building One-File Version ===")
    run_command(["pyinstaller", "build.spec", "--clean", "--noconfirm"], cwd=spec_dir)
    return dist_dir / "STM32教学管理系统.exe"


def build_onedir(spec_dir, dist_dir):
    """构建目录版本"""
    print("\n=== Building Directory Version ===")
    run_command(["pyinstaller", "build.spec", "--clean", "--noconfirm", "--onefile-mode=false"], cwd=spec_dir)
    return dist_dir / "STM32教学管理系统"


def create_release_package(source, output_dir, version="2.6.0"):
    """创建发布包"""
    release_name = f"STM32教学管理系统-v{version}"
    release_dir = output_dir / release_name
    zip_path = output_dir / f"{release_name}.zip"

    # 清理旧文件
    if release_dir.exists():
        shutil.rmtree(release_dir)
    if zip_path.exists():
        zip_path.unlink()

    # 创建发布目录
    release_dir.mkdir(parents=True, exist_ok=True)

    # 复制主文件
    if source.is_dir():
        # 目录模式 - 复制整个目录
        shutil.copytree(source, release_dir / source.name, dirs_exist_ok=True)
        exe_path = release_dir / source.name / "STM32教学管理系统.exe"
    else:
        # 单文件模式
        shutil.copy2(source, release_dir / source.name)
        exe_path = release_dir / source.name

    # 复制文档文件
    docs = {
        "README.txt": """# STM32 教学管理系统

版本: 2.6.0
发布日期: {date}

## 快速开始
1. 双击 STM32教学管理系统.exe 启动
2. 首次使用请在设置中配置项目路径

## 系统要求
- Windows 10/11 (64位)
- 4GB+ 内存
- 200MB 磁盘空间

## 功能
- 查重检测
- 评分评估
- 反馈生成
- 报告输出

## 卸载
直接删除程序文件夹即可

Copyright (c) 2024-2026 MCU Research
""".format(date=datetime.now().strftime("%Y-%m-%d")),

        "CHANGELOG.txt": """更新日志

v2.6.0 (2024-06-12)
- 添加多班级处理功能
- 优化安全模块打包
- 添加版本信息和图标
- 修复文件对话框定位问题

v2.5.0 (2024-06-11)
- 安全增强版
- 路径验证、ZIP验证、XML解析安全化

v2.4.0 (2024-05-30)
- 配置化权重
- 增强语义检测

v2.0.0 (2024-04-20)
- 模块化架构重构
""",
    }

    for filename, content in docs.items():
        (release_dir / filename).write_text(content, encoding='utf-8')

    # 创建 ZIP 包
    print(f"\n=== Creating ZIP Package ===")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in release_dir.rglob('*'):
            if file.is_file():
                arcname = file.relative_to(output_dir)
                zf.write(file, arcname)

    file_size = zip_path.stat().st_size / (1024 * 1024)
    print(f"\n[OK] Release package created: {zip_path}")
    print(f"     Size: {file_size:.1f} MB")

    return zip_path


def main():
    """主函数"""
    script_dir = Path(__file__).parent.absolute()
    dist_dir = script_dir / "dist"
    release_dir = script_dir / "release"
    version = "2.6.0"

    # 创建 release 目录
    release_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("STM32 教学管理系统 - 发布打包")
    print("=" * 60)
    print(f"Version: {version}")
    print(f"Script: {script_dir}")
    print(f"Output: {release_dir}")

    # 构建模式选择
    print("\n请选择构建模式:")
    print("  1. 单文件模式 (One-File) - 小体积，分发方便")
    print("  2. 目录模式 (Directory) - 启动快")
    print("  3. 两种模式都构建")

    choice = input("\n请输入选择 [1-3, 默认=1]: ").strip() or "1"

    if choice == "1":
        # 单文件模式
        exe = build_onefile(script_dir, dist_dir)
        create_release_package(exe, release_dir, version)
    elif choice == "2":
        # 目录模式
        dir_path = build_onedir(script_dir, dist_dir)
        create_release_package(dir_path, release_dir, version)
    elif choice == "3":
        # 两种模式
        exe = build_onefile(script_dir, dist_dir)
        create_release_package(exe, release_dir / "onefile", version)

        dir_path = build_onedir(script_dir, dist_dir)
        create_release_package(dir_path, release_dir / "onedir", version)
    else:
        print("[ERROR] Invalid choice")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Release build completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
