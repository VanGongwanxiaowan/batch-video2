"""配置验证模块

在启动时验证所有关键配置，确保系统可以正常运行。
"""

from typing import Any, List, Optional

from pydantic import Field, field_validator

from core.logging_config import setup_logging

logger = setup_logging("core.config.validation")


class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_backend_config(config) -> List[str]:
        """
        验证后端配置
        
        Returns:
            错误列表，如果为空则表示验证通过
        """
        errors = []
        
        # 验证数据库URL
        if not config.DATABASE_URL or config.DATABASE_URL == "":
            errors.append("DATABASE_URL 不能为空")
        
        # 验证OSS配置
        if not config.OSS_ACCESS_KEY_ID or config.OSS_ACCESS_KEY_ID == "your_access_key_id":
            errors.append("OSS_ACCESS_KEY_ID 未正确配置")
        
        if not config.OSS_ACCESS_KEY_SECRET or config.OSS_ACCESS_KEY_SECRET == "your_access_key_secret":
            errors.append("OSS_ACCESS_KEY_SECRET 未正确配置")
        
        # 验证SECRET_KEY
        if not config.ACCESS_SECRET or config.ACCESS_SECRET == "":
            errors.append("ACCESS_SECRET 不能为空，这是安全风险")
        
        # 验证CORS配置
        if not config.ALLOWED_ORIGINS or len(config.ALLOWED_ORIGINS) == 0:
            errors.append("ALLOWED_ORIGINS 不能为空")
        
        if "*" in config.ALLOWED_ORIGINS and config.ALLOWED_ORIGINS != ["*"]:
            errors.append("ALLOWED_ORIGINS 不能同时包含 '*' 和其他源")
        
        return errors
    
    @staticmethod
    def validate_worker_config(config) -> List[str]:
        """
        验证Worker配置
        
        Returns:
            错误列表，如果为空则表示验证通过
        """
        errors = []
        
        # 验证数据库URL
        if not config.DATABASE_URL or config.DATABASE_URL == "":
            errors.append("DATABASE_URL 不能为空")
        
        # 验证OSS配置
        if not config.OSS_ACCESS_KEY_ID or config.OSS_ACCESS_KEY_ID == "your_access_key_id":
            errors.append("OSS_ACCESS_KEY_ID 未正确配置")
        
        if not config.OSS_ACCESS_KEY_SECRET or config.OSS_ACCESS_KEY_SECRET == "your_access_key_secret":
            errors.append("OSS_ACCESS_KEY_SECRET 未正确配置")
        
        # 验证SECRET_KEY
        if not config.ACCESS_SECRET or config.ACCESS_SECRET == "":
            errors.append("ACCESS_SECRET 不能为空，这是安全风险")
        
        # 验证外部服务URL
        required_urls = [
            ("TTS_SERVER_URL", config.TTS_SERVER_URL),
            ("AZURE_TTS_SERVER_URL", config.AZURE_TTS_SERVER_URL),
            ("FLUX_SERVER_URL", config.FLUX_SERVER_URL),
            ("AI_IMAGE_GEN_API_URL", config.AI_IMAGE_GEN_API_URL),
            ("HUMAN_SERVICE_URL", config.HUMAN_SERVICE_URL),
        ]
        
        for name, url in required_urls:
            if not url or url == "":
                errors.append(f"{name} 不能为空")
        
        return errors
    
    @staticmethod
    def validate_and_raise(config: Any, config_type: str = "backend") -> None:
        """
        验证配置并在失败时抛出异常
        
        Args:
            config: 配置对象
            config_type: 配置类型 ("backend" 或 "worker")
            
        Raises:
            ConfigurationException: 如果配置验证失败
        """
        if config_type == "backend":
            errors = ConfigValidator.validate_backend_config(config)
        elif config_type == "worker":
            errors = ConfigValidator.validate_worker_config(config)
        else:
            raise ValueError(f"未知的配置类型: {config_type}")
        
        if errors:
            error_msg = f"配置验证失败 ({config_type}):\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"配置验证通过 ({config_type})")

