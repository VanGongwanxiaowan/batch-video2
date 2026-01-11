"""图像描述生成器工厂模块

提供生成器创建和管理的工厂类。
"""
from typing import Union

from core.logging_config import setup_logging

from .base_generator import ImageDescriptionGenerator
from .config import GENERATE_TYPE_V1, GeneratorConfig
from .v1_generator import V1ImageDescriptionGenerator
from .v2_generator import V2ImageDescriptionGenerator

logger = setup_logging("worker.utils.image_description.factory")


class GeneratorFactory:
    """图像描述生成器工厂类。
    
    负责根据配置创建合适的生成器实例，封装生成器选择逻辑。
    """
    
    @staticmethod
    def create(
        config: GeneratorConfig,
        generate_type: str = GENERATE_TYPE_V1,
    ) -> Union[V1ImageDescriptionGenerator, V2ImageDescriptionGenerator]:
        """创建图像描述生成器。
        
        根据generate_type选择V1或V2生成器。
        
        Args:
            config: 生成器配置
            generate_type: 生成方式类型
                - "none"或空字符串：使用V1生成器（逐行格式）
                - 其他值：使用V2生成器（JSON格式）
        
        Returns:
            图像描述生成器实例
            
        Example:
            >>> config = GeneratorConfig(
            ...     model="deepseek-v3",
            ...     baseprompt="Generate an image",
            ...     prefix="A beautiful",
            ...     prompt_cover_image="Cover image"
            ... )
            >>> generator = GeneratorFactory.create(config, generate_type="v2")
            >>> isinstance(generator, V2ImageDescriptionGenerator)
            True
        """
        if generate_type in ["", GENERATE_TYPE_V1]:
            logger.info("使用V1生成器（逐行格式）")
            return V1ImageDescriptionGenerator(
                model=config.model,
                baseprompt=config.baseprompt,
                prefix=config.prefix,
                prompt_cover_image=config.prompt_cover_image,
            )
        else:
            logger.info("使用V2生成器（JSON格式）")
            return V2ImageDescriptionGenerator(
                model=config.model,
                baseprompt=config.baseprompt,
                prefix=config.prefix,
                prompt_cover_image=config.prompt_cover_image,
            )
    
    @staticmethod
    def create_from_config(config: GeneratorConfig) -> ImageDescriptionGenerator:
        """从配置创建生成器（使用默认V1方式）。
        
        Args:
            config: 生成器配置
        
        Returns:
            图像描述生成器实例（默认V1）
        """
        return GeneratorFactory.create(config, generate_type=GENERATE_TYPE_V1)




