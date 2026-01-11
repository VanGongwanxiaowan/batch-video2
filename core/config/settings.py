"""共享配置定义模块。

使用Pydantic Settings提供类型安全、环境变量支持的配置管理。
"""

from functools import lru_cache
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    """通用配置基类，使用Pydantic Settings进行配置管理。

    所有服务的配置类都应该继承此类。支持：
    - 环境变量自动加载
    - 类型验证
    - 默认值设置
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",  # 允许额外的配置字段
    )


class AppConfig(BaseConfig):
    """应用级配置。

    定义应用程序的基本配置项，如应用名称、版本、环境等。
    """

    APP_NAME: str = "BatchShort1"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "testing", "production"] = "development"
    BATCHSHORT_BASE_DIR: Optional[str] = None


@lru_cache()
def get_app_config() -> AppConfig:
    """获取缓存的应用程序配置实例。

    Returns:
        AppConfig: 应用程序配置对象

    注意：
        - 使用lru_cache缓存配置实例，避免重复创建
        - 如果配置变更，需要重启应用才能生效
    """
    return AppConfig()


