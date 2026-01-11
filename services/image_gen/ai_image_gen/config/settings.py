"""AI Image Generation Service 配置管理."""
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator

from core.config import BaseConfig, PathManager, get_path_manager


class ImageGenSettings(BaseConfig):
    """AI Image Generation Service 配置类."""
    
    APP_NAME: str = Field(default="AI Image Generation Service", description="应用名称")
    DEBUG_MODE: bool = Field(default=False, description="调试模式")
    
    # Database settings
    DATABASE_URL: str = Field(
        default="",
        description="数据库连接URL，不能为空"
    )
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field(
        default="",
        description="Kafka引导服务器地址，不能为空"
    )
    KAFKA_USERNAME: str = Field(default="", description="Kafka用户名")
    KAFKA_PASSWORD: str = Field(default="", description="Kafka密码")
    KAFKA_SECURITY_PROTOCOL: str = Field(default="SASL_PLAINTEXT", description="Kafka安全协议")
    KAFKA_SASL_MECHANISM: str = Field(default="PLAIN", description="Kafka SASL机制")
    KAFKA_CONSUMER_GROUP_ID: str = Field(
        default="gpu_worker_group",
        description="Kafka消费者组ID"
    )
    
    @field_validator("DATABASE_URL", "KAFKA_BOOTSTRAP_SERVERS")
    @classmethod
    def validate_required_fields(cls, v: str, info) -> str:
        """验证必需字段
        
        Args:
            v: 字段值
            info: 验证信息
            
        Returns:
            str: 验证后的值
            
        Raises:
            ValueError: 如果字段为空
        """
        if not v or v == "":
            field_name = info.field_name
            raise ValueError(f"{field_name} 不能为空，必须从环境变量配置")
        return v
    
    @field_validator("KAFKA_PASSWORD")
    @classmethod
    def validate_kafka_password(cls, v: str, info) -> str:
        """验证Kafka密码
        
        Args:
            v: 密码值
            info: 验证信息
            
        Returns:
            str: 验证后的密码值
            
        Raises:
            ValueError: 如果密码为空且需要认证
        """
        # 如果KAFKA_USERNAME不为空，则密码也不能为空
        if info.data.get("KAFKA_USERNAME") and (not v or v == ""):
            raise ValueError("KAFKA_PASSWORD 不能为空，当KAFKA_USERNAME已设置时必须提供密码")
        return v
    KAFKA_TOPICS: str = Field(
        default="sdxl_tasks,sd15_tasks,flux_tasks,insc_tasks",
        description="Kafka主题列表（逗号分隔）"
    )
    PRIORITY_KAFKA_TOPICS: str = Field(
        default="online_task",
        description="优先处理的Kafka主题"
    )
    
    # Model management settings
    MODEL_CACHE_DIR: Optional[str] = Field(
        default=None,
        description="模型缓存目录（如果未指定，将使用PathManager的默认路径）"
    )
    GENERATED_IMAGES_DIR: Optional[str] = Field(
        default=None,
        description="生成的图片存储目录（如果未指定，将使用PathManager的默认路径）"
    )
    
    # Worker specific settings
    WORKER_BATCH_SIZE: int = Field(
        default=1,
        ge=1,
        description="一次处理的图片数量"
    )
    WORKER_MODEL_SWITCH_THRESHOLD: int = Field(
        default=6,
        ge=1,
        description="触发切换到另一个模型的任务数量"
    )
    API_BASE_URL: str = Field(
        default="http://localhost:8000",
        description="API服务的基础URL"
    )
    
    @property
    def path_manager(self) -> PathManager:
        """获取路径管理器."""
        return get_path_manager(self.BATCHSHORT_BASE_DIR)
    
    @property
    def model_cache_path(self) -> Path:
        """获取模型缓存目录路径."""
        if self.MODEL_CACHE_DIR:
            return Path(self.MODEL_CACHE_DIR).expanduser().resolve()
        # 使用PathManager的默认模型目录
        return self.path_manager.worker_models_dir
    
    @property
    def generated_images_path(self) -> Path:
        """获取生成的图片存储目录路径."""
        if self.GENERATED_IMAGES_DIR:
            return Path(self.GENERATED_IMAGES_DIR).expanduser().resolve()
        # 使用PathManager的默认临时目录
        return self.path_manager.temp_dir / "generated_images"
    
    def __getattribute__(self, name: str):
        """向后兼容：当访问 MODEL_CACHE_DIR 或 GENERATED_IMAGES_DIR 时返回字符串路径."""
        # 对于已设置的字段，直接返回原始值
        if name in ('MODEL_CACHE_DIR', 'GENERATED_IMAGES_DIR'):
            try:
                # 使用 object.__getattribute__ 避免递归
                value = object.__getattribute__(self, name)
                # 如果是 None，返回计算后的默认路径字符串
                if value is None:
                    if name == 'MODEL_CACHE_DIR':
                        model_cache_path = object.__getattribute__(self, 'model_cache_path')
                        return str(model_cache_path)
                    elif name == 'GENERATED_IMAGES_DIR':
                        generated_images_path = object.__getattribute__(self, 'generated_images_path')
                        return str(generated_images_path)
                # 如果已设置，返回原始字符串值
                return value
            except AttributeError:
                # 如果属性不存在，使用计算后的路径
                if name == 'MODEL_CACHE_DIR':
                    model_cache_path = object.__getattribute__(self, 'model_cache_path')
                    return str(model_cache_path)
                elif name == 'GENERATED_IMAGES_DIR':
                    generated_images_path = object.__getattribute__(self, 'generated_images_path')
                    return str(generated_images_path)
        return super().__getattribute__(name)
    
    def get_model_configs(self) -> dict:
        """
        动态生成模型配置字典。
        使用此方法而不是直接访问字段，以确保路径正确解析。
        
        Returns:
            dict: 模型配置字典
        """
        model_cache_dir = self.model_cache_path
        return {
            "SDXL": {
                "path": str(model_cache_dir / "SD_XL" / "128078"),
                "lora": None  # SDXL Lora path if applicable
            },
            "SD15": {
                "path": str(model_cache_dir / "stable-diffusion-v1-5"),
                "lora": str(model_cache_dir / "stable-diffusion-v1-5_loras")
            },
            "FLUX": {
                "path": str(model_cache_dir / "flux-1-dev"),
                "lora": str(model_cache_dir / "flux-1-dev_loras")
            },
            "INSC": {
                "path": str(model_cache_dir / "flux-1-dev"),
                "lora": str(model_cache_dir / "flux-1-dev_loras"),
                "ip_adapter_path": str(model_cache_dir / "ipadapter" / "instantcharacter_ip-adapter.bin"),
                "image_encoder_path": str(model_cache_dir / "google" / "siglip-so400m-patch14-384"),
                "image_encoder_2_path": str(model_cache_dir / "facebook" / "dinov2-giant"),
            }
        }
    
    # 为了向后兼容，保留 MODEL_CONFIGS 作为属性访问
    @property
    def MODEL_CONFIGS(self) -> dict:
        """向后兼容的属性访问器"""
        return self.get_model_configs()


# 为了向后兼容，保留 Settings 作为 ImageGenSettings 的别名
Settings = ImageGenSettings


@lru_cache()
def get_settings() -> ImageGenSettings:
    """获取缓存的配置实例."""
    return ImageGenSettings()