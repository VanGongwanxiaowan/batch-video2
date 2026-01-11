"""核心配置工具模块。

提供统一的配置管理功能，包括：
- BaseConfig: 基础配置类
- AppConfig: 应用级配置
- PathManager: 路径管理器
- constants: 配置常量（RetryConfig、DatabaseConfig等）
- status: 执行状态枚举（ExecutionStatus、JobStatus）
- api: API 端点常量（APIEndpoints、ConfigFilePaths）
- celery_config: Celery 分布式任务队列配置
"""

from .api import (
    APIEndpoint,
    APIEndpoints,
    ConfigFilePaths,
    ServiceURLs,
    get_endpoint_url,
)
from .constants import (
    APIConfig,
    ColorConfig,
    DatabaseConfig,
    DatabasePoolConfig,
    FFmpegConfigConstants,
    FileConfig,
    HighAvailabilityConfig,
    ImageConfig,
    ImageGenConfig,
    JobConfig,
    MonitoringConfig,
    OSSConfig,
    PathConfigConstants,
    RetryConfig,
    SecurityConfig,
    TextConfig,
    TimeoutConfig,
    TTSConfig,
    VideoConfig,
    VideoProcessingConfigConstants,
    WorkerConfig,
)
from .celery_config import (
    CeleryConfig,
    celery_app_config,
    celery_beat_schedule,
    get_celery_broker_url,
    get_celery_config,
    get_celery_result_backend,
)
from .paths import PathManager, get_path_manager
from .settings import AppConfig, BaseConfig, get_app_config
# 执行状态枚举
from .status import (
    ExecutionStatus,
    JobStatus,
    get_status,
    is_failure_status,
    is_success_status,
    is_terminal_status,
)

__all__ = [
    "BaseConfig",
    "AppConfig",
    "get_app_config",
    "PathManager",
    "get_path_manager",
    # 配置常量
    "RetryConfig",
    "DatabaseConfig",
    "DatabasePoolConfig",
    "FileConfig",
    "TextConfig",
    "JobConfig",
    "OSSConfig",
    "ImageConfig",
    "VideoConfig",
    "TimeoutConfig",
    "TTSConfig",
    "WorkerConfig",
    "ImageGenConfig",
    "APIConfig",
    "VideoProcessingConfigConstants",
    "FFmpegConfigConstants",
    "ColorConfig",
    "PathConfigConstants",
    "MonitoringConfig",
    "SecurityConfig",
    "HighAvailabilityConfig",
    # 执行状态枚举
    "ExecutionStatus",
    "JobStatus",
    "get_status",
    "is_terminal_status",
    "is_success_status",
    "is_failure_status",
    # API 端点常量
    "APIEndpoint",
    "APIEndpoints",
    "ConfigFilePaths",
    "ServiceURLs",
    "get_endpoint_url",
    # Celery 配置
    "CeleryConfig",
    "get_celery_config",
    "celery_app_config",
    "celery_beat_schedule",
    "get_celery_broker_url",
    "get_celery_result_backend",
]


