from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator

from core.config import BaseConfig, PathManager, get_path_manager


class BackendConfig(BaseConfig):
    """Backend service configuration."""

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
    ASSERT_PATH: str = Field(
        default="",
        description="资源路径"
    )
    
    # CORS配置 - 生产环境必须限制
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="允许的CORS源，生产环境必须明确指定，不能使用 '*'"
    )
    ALLOWED_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="允许的HTTP方法"
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization"],
        description="允许的HTTP头"
    )
    
    # JWT配置
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60 * 24 * 7,  # 7天，而不是2年
        description="JWT访问令牌过期时间（分钟）"
    )
    
    # 速率限制配置
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="是否启用速率限制"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="每分钟允许的请求数"
    )
    
    # 环境配置
    ENVIRONMENT: str = Field(
        default="production",
        description="运行环境: development, testing, production"
    )
    
    # API配置
    API_VERSION: str = Field(
        default="v1",
        description="API版本号"
    )
    API_PREFIX: str = Field(
        default="/api",
        description="API前缀"
    )
    
    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: List[str], info) -> List[str]:
        """验证CORS配置"""
        if not v:
            raise ValueError("ALLOWED_ORIGINS 不能为空")
        # 在生产环境中，不允许使用 '*'
        if info.data.get("ENVIRONMENT") == "production" and "*" in v:
            raise ValueError("生产环境不允许使用 '*' 作为CORS源")
        return v
    
    @field_validator("ACCESS_SECRET")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """验证密钥"""
        if not v or v == "":
            raise ValueError("ACCESS_SECRET 不能为空，这是安全风险")
        if len(v) < 32:
            raise ValueError("ACCESS_SECRET 长度至少为32个字符")
        return v

    @property
    def path_manager(self) -> PathManager:
        return get_path_manager(self.BATCHSHORT_BASE_DIR)

    @property
    def assets_path(self) -> Path:
        if self.ASSERT_PATH:
            return Path(self.ASSERT_PATH)
        return self.path_manager.worker_assets_dir


@lru_cache()
def get_backend_config() -> BackendConfig:
    """获取后端配置并验证"""
    from core.config.validation import ConfigValidator
    
    config = BackendConfig()
    # 在非开发环境下验证配置
    if config.ENVIRONMENT != "development":
        ConfigValidator.validate_and_raise(config, "backend")
    return config


settings = get_backend_config()