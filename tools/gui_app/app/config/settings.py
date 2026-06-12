"""
配置管理模块

提供项目配置的保存、加载和管理功能
"""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from app.models.domain import ProjectConfig, ExperimentType, MultiClassProjectConfig, ClassConfig


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件存储目录，默认为用户主目录/.stm32_teaching_manager
        """
        if config_dir is None:
            home = Path.home()
            config_dir = home / ".stm32_teaching_manager"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 最近项目列表
        self.recent_projects_file = self.config_dir / "recent_projects.json"

    def save_project(self, config: ProjectConfig, project_path: Optional[Path] = None) -> Path:
        """
        保存项目配置

        Args:
            config: 项目配置
            project_path: 保存路径，如果为None则自动生成

        Returns:
            保存的配置文件路径
        """
        # 更新修改时间
        config.modified_at = datetime.now().isoformat()
        if not config.created_at:
            config.created_at = config.modified_at

        # 确定保存路径
        if project_path is None:
            project_dir = config.experiment_dir / ".teaching_manager"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_path = project_dir / "project_config.json"

        # 保存配置
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)

        # 添加到最近项目列表
        self.add_recent_project(project_path)

        return project_path

    def load_project(self, project_path: Path) -> Optional[ProjectConfig]:
        """
        加载项目配置

        Args:
            project_path: 项目配置文件路径

        Returns:
            项目配置，如果加载失败返回None
        """
        if not project_path.exists():
            return None

        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            config = ProjectConfig.from_dict(data)

            # 添加到最近项目列表
            self.add_recent_project(project_path)

            return config
        except Exception as e:
            print(f"加载项目配置失败: {e}")
            return None

    def add_recent_project(self, project_path: Path) -> None:
        """添加到最近项目列表"""
        recent = self.get_recent_projects()

        # 移除已存在的相同路径
        recent = [p for p in recent if p['path'] != str(project_path)]

        # 添加到开头
        project_name = project_path.parent.parent.name  # 实验目录名
        recent.insert(0, {
            'path': str(project_path),
            'name': project_name,
            'opened_at': datetime.now().isoformat()
        })

        # 最多保留10个
        recent = recent[:10]

        # 保存
        with open(self.recent_projects_file, 'w', encoding='utf-8') as f:
            json.dump(recent, f, ensure_ascii=False, indent=2)

    def get_recent_projects(self) -> List[dict]:
        """获取最近项目列表"""
        if not self.recent_projects_file.exists():
            return []

        try:
            with open(self.recent_projects_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, IOError) as e:
            # 日志记录错误
            print(f"Warning: Failed to load recent projects: {e}")
            return []

    def clear_recent_projects(self) -> None:
        """清空最近项目列表"""
        if self.recent_projects_file.exists():
            self.recent_projects_file.unlink()

    def create_default_config(self) -> ProjectConfig:
        """创建默认配置"""
        return ProjectConfig(
            class_name="新班级",
            experiment_type=ExperimentType.CUSTOM,
            experiment_dir=Path.cwd(),
            suspicious_threshold=60.0,
            high_similarity_threshold=70.0,
            plagiarism_threshold=85.0,
            created_at=datetime.now().isoformat()
        )

    def save_multi_class_project(self, config: MultiClassProjectConfig, project_path: Optional[Path] = None) -> Path:
        """
        保存多班级项目配置

        Args:
            config: 多班级项目配置
            project_path: 保存路径，如果为None则自动生成

        Returns:
            保存的配置文件路径
        """
        # 更新修改时间
        config.modified_at = datetime.now().isoformat()
        if not config.created_at:
            config.created_at = config.modified_at

        # 确定保存路径
        if project_path is None and config.output_dir:
            project_dir = config.output_dir / ".teaching_manager"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_path = project_dir / "multi_class_config.json"
        elif project_path is None:
            project_dir = self.config_dir / "multi_class_projects"
            project_dir.mkdir(parents=True, exist_ok=True)
            project_path = project_dir / f"{config.project_id}_multi_class_config.json"

        # 保存配置
        with open(project_path, 'w', encoding='utf-8') as f:
            json.dump(config.to_dict(), f, ensure_ascii=False, indent=2)

        # 添加到最近项目列表
        self.add_recent_project(project_path)

        return project_path

    def load_multi_class_project(self, project_path: Path) -> Optional[MultiClassProjectConfig]:
        """
        加载多班级项目配置

        Args:
            project_path: 项目配置文件路径

        Returns:
            多班级项目配置，如果加载失败返回None
        """
        if not project_path.exists():
            return None

        try:
            with open(project_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            config = MultiClassProjectConfig.from_dict(data)

            # 添加到最近项目列表
            self.add_recent_project(project_path)

            return config
        except Exception as e:
            print(f"加载多班级项目配置失败: {e}")
            return None

    def create_default_multi_class_config(self) -> MultiClassProjectConfig:
        """创建默认多班级配置"""
        return MultiClassProjectConfig(
            project_id=f"default_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            project_name="新多班级项目",
            classes=[],
            enable_cross_class_detection=True,
            shared_threshold=60.0,
            created_at=datetime.now().isoformat()
        )
