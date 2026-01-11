from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator

from core.config import BaseConfig, PathManager, get_path_manager


class WorkerConfig(BaseConfig):
    """Worker service configuration."""

    DATABASE_URL: str = Field(
        default="",
        description="数据库连接URL，不能为空"
    )
    OSS_ACCESS_KEY_ID: str = Field(
        default="",
        description="OSS访问密钥ID"
    )
    OSS_ACCESS_KEY_SECRET: str = Field(
        default="",
        description="OSS访问密钥Secret"
    )
    OSS_ENDPOINT: str = Field(
        default="",
        description="OSS端点"
    )
    OSS_BUCKET_NAME: str = Field(
        default="",
        description="OSS存储桶名称"
    )
    ALIYUN_RAM_ROLE_ARN: str = Field(
        default="",
        description="阿里云RAM角色ARN"
    )
    ACCESS_SECRET: str = Field(
        default="",
        description="JWT密钥，不能为空"
    )
    BILLS_SERVICE_URL: str = Field(
        default="http://localhost:8303",
        description="账单服务URL"
    )
    BACKEND_SERVER_URL: str = Field(
        default="http://localhost:8006",
        description="后端服务URL"
    )
    TTS_SERVER_URL: str = Field(
        default="http://127.0.0.1:8007",
        description="TTS服务URL"
    )
    AZURE_TTS_SERVER_URL: str = Field(
        default="http://127.0.0.1:8008",
        description="Azure TTS服务URL"
    )
    FLUX_SERVER_URL: str = Field(
        default="http://127.0.0.1:8009",
        description="Flux服务URL"
    )
    AI_IMAGE_GEN_API_URL: str = Field(
        default="http://127.0.0.1:8010",
        description="AI图像生成服务URL"
    )
    HUMAN_SERVICE_URL: str = Field(
        default="http://localhost:8308",
        description="数字人服务URL"
    )
    OCR_SERVICE_URL: str = Field(
        default="http://localhost:8222",
        description="OCR服务URL"
    )
    LLM_API_KEY: str = Field(
        default="",
        description="LLM API密钥"
    )
    LLM_API_BASE: str = Field(
        default="http://localhost:10001",
        description="LLM API基础URL"
    )
    
    # Worker并发配置
    MAX_CONCURRENT_JOBS: int = Field(
        default=1,
        ge=1,
        le=100,
        description="最大并发任务数"
    )
    
    # 任务轮询配置
    JOB_POLL_INTERVAL_SECONDS: int = Field(
        default=10,
        ge=1,
        le=300,
        description="任务轮询间隔（秒）"
    )
    
    # 重试配置
    MAX_RETRY_COUNT: int = Field(
        default=3,
        ge=0,
        le=10,
        description="最大重试次数"
    )
    RETRY_BACKOFF_MULTIPLIER: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="重试指数退避乘数"
    )
    
    # 环境配置
    ENVIRONMENT: str = Field(
        default="production",
        description="运行环境: development, testing, production"
    )
    
    @field_validator("ACCESS_SECRET")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """验证密钥
        
        Args:
            v: 密钥值
            
        Returns:
            str: 验证后的密钥值
            
        Raises:
            ValueError: 如果密钥为空或长度不足
        """
        if not v or v == "":
            raise ValueError("ACCESS_SECRET 不能为空，这是安全风险")
        if len(v) < 32:
            raise ValueError("ACCESS_SECRET 长度至少为32个字符")
        return v

    WORKER_HUMAN_ASSETS_DIR: Optional[str] = None
    WORKER_HUMAN_CONFIG_PATH: Optional[str] = None
    WORKER_FONT_DIR: Optional[str] = None
    WORKER_MODEL_CACHE_DIR: Optional[str] = None
    WORKER_BG_AUDIO_DIR: Optional[str] = None

    @property
    def path_manager(self) -> PathManager:
        return get_path_manager(self.BATCHSHORT_BASE_DIR)

    @property
    def assets_path(self) -> Path:
        return self.path_manager.worker_assets_dir

    @property
    def human_assets_path(self) -> Path:
        if self.WORKER_HUMAN_ASSETS_DIR:
            return Path(self.WORKER_HUMAN_ASSETS_DIR)
        return self.path_manager.human_assets_dir

    @property
    def human_config_path(self) -> Path:
        if self.WORKER_HUMAN_CONFIG_PATH:
            return Path(self.WORKER_HUMAN_CONFIG_PATH)
        return self.path_manager.config_dir / "data.json"

    @property
    def font_dir(self) -> Path:
        if self.WORKER_FONT_DIR:
            return Path(self.WORKER_FONT_DIR)
        return Path(__file__).resolve().parent / "utils" / "ttfs"

    @property
    def model_cache_dir(self) -> Path:
        if self.WORKER_MODEL_CACHE_DIR:
            return Path(self.WORKER_MODEL_CACHE_DIR)
        return self.path_manager.worker_models_dir

    @property
    def bg_audio_dir(self) -> Path:
        if self.WORKER_BG_AUDIO_DIR:
            return Path(self.WORKER_BG_AUDIO_DIR)
        return Path(__file__).resolve().parent / "utils" / "bg"


@lru_cache()
def get_worker_config() -> WorkerConfig:
    """获取Worker配置并验证"""
    from core.config.validation import ConfigValidator
    
    config = WorkerConfig()
    # 在非开发环境下验证配置
    if config.ENVIRONMENT != "development":
        ConfigValidator.validate_and_raise(config, "worker")
    return config


@lru_cache()
def get_worker_path_manager() -> PathManager:
    return get_worker_config().path_manager


settings = get_worker_config()
path_manager = get_worker_path_manager()