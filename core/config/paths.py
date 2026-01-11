"""路径管理工具模块。

提供统一的文件系统路径管理功能，确保所有服务使用一致的路径结构。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Union

from .settings import get_app_config

# 默认基础目录路径
DEFAULT_BASE_DIR = Path("/app/data")


class PathManager:
    """集中式文件系统路径管理器。

    管理应用程序中所有文件路径，包括：
    - 基础目录
    - 资源目录（assets）
    - 日志目录
    - 临时目录
    - 缓存目录
    - 用户和任务特定目录

    所有目录在创建时会自动创建，确保目录存在。
    """

    def __init__(self, base_dir: Optional[Union[str, Path]] = None) -> None:
        """初始化路径管理器。

        Args:
            base_dir: 基础目录路径。如果为None，则从配置或默认值获取。
                     支持字符串或Path对象，会自动展开用户目录并解析为绝对路径。
        """
        app_config = get_app_config()
        resolved_base = (
            Path(base_dir)
            if base_dir
            else Path(app_config.BATCHSHORT_BASE_DIR)
            if app_config.BATCHSHORT_BASE_DIR
            else DEFAULT_BASE_DIR
        )
        self._base_dir = resolved_base.expanduser().resolve()
        self._ensure_base_directories()

    def _ensure_base_directories(self) -> None:
        """确保所有基础目录存在。

        在初始化时自动创建所有必需的目录，避免运行时目录不存在的问题。
        """
        for path in {
            self.base_dir,
            self.assets_dir,
            self.shared_dir,
            self.worker_dir,
            self.worker_assets_dir,
            self.logs_dir,
            self.cache_dir,
            self.temp_dir,
        }:
            path.mkdir(parents=True, exist_ok=True)

    @property
    def base_dir(self) -> Path:
        """获取基础目录路径。

        Returns:
            Path: 基础目录的Path对象
        """
        return self._base_dir

    @property
    def assets_dir(self) -> Path:
        """获取资源目录路径。

        Returns:
            Path: 资源目录的Path对象
        """
        return self.base_dir / "assets"

    @property
    def shared_dir(self) -> Path:
        """获取共享目录路径。

        Returns:
            Path: 共享目录的Path对象
        """
        return self.base_dir / "shared"

    @property
    def worker_dir(self) -> Path:
        """获取Worker服务目录路径。

        Returns:
            Path: Worker目录的Path对象
        """
        return self.base_dir / "worker"

    @property
    def worker_assets_dir(self) -> Path:
        """获取Worker资源目录路径。

        Returns:
            Path: Worker资源目录的Path对象

        注意：
            使用 "assets" 作为标准目录名，修复早期拼写错误 "assrts"
        """
        path = self.worker_dir / "assets"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def worker_fonts_dir(self) -> Path:
        """获取Worker字体目录路径。

        Returns:
            Path: Worker字体目录的Path对象
        """
        path = self.worker_dir / "fonts"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def worker_models_dir(self) -> Path:
        """获取Worker模型目录路径。

        Returns:
            Path: Worker模型目录的Path对象
        """
        path = self.worker_dir / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def human_assets_dir(self) -> Path:
        """获取数字人资源目录路径。

        Returns:
            Path: 数字人资源目录的Path对象
        """
        path = self.shared_dir / "human"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def config_dir(self) -> Path:
        """获取配置目录路径。

        Returns:
            Path: 配置目录的Path对象
        """
        path = self.shared_dir / "config"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def logs_dir(self) -> Path:
        """获取日志目录路径。

        Returns:
            Path: 日志目录的Path对象
        """
        return self.base_dir / "logs"

    @property
    def cache_dir(self) -> Path:
        """获取缓存目录路径。

        Returns:
            Path: 缓存目录的Path对象
        """
        return self.base_dir / "cache"

    @property
    def temp_dir(self) -> Path:
        """获取临时目录路径。

        Returns:
            Path: 临时目录的Path对象
        """
        return self.base_dir / "temp"

    def get_user_assets_dir(self, user_id: Union[str, int]) -> Path:
        """获取用户资源目录路径。

        Args:
            user_id: 用户ID，可以是字符串或整数

        Returns:
            Path: 用户资源目录的Path对象
        """
        path = self.worker_assets_dir / "users" / str(user_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_job_assets_dir(
        self, job_id: Union[str, int], user_id: Union[str, int]
    ) -> Path:
        """获取任务资源目录路径。

        Args:
            job_id: 任务ID，可以是字符串或整数
            user_id: 用户ID，可以是字符串或整数

        Returns:
            Path: 任务资源目录的Path对象
        """
        path = self.get_user_assets_dir(user_id) / f"job_{job_id}"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_path_manager(base_dir: Optional[Union[str, Path]] = None) -> PathManager:
    """获取缓存的路径管理器实例。

    Args:
        base_dir: 基础目录路径。如果为None，则使用默认路径。
                 注意：由于使用了lru_cache，相同base_dir会返回同一个实例。

    Returns:
        PathManager: 路径管理器实例

    注意：
        - 使用lru_cache缓存路径管理器，避免重复创建
        - 如果base_dir为None，所有调用将返回同一个实例
    """
    return PathManager(base_dir)


