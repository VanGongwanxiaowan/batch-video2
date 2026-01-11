"""图像描述生成器配置模块

定义配置数据类和常量。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# 常量定义
DEFAULT_MODEL = "deepseek-v3"
"""默认使用的LLM模型名称"""

GENERATE_TYPE_V1 = "none"
"""V1生成方式标识（向后兼容）"""

GENERATE_TYPE_V2 = "v2"
"""V2生成方式标识"""


@dataclass
class GeneratorConfig:
    """生成器配置数据类。
    
    封装所有生成器初始化所需的参数，提供类型安全和默认值支持。
    
    Attributes:
        model: LLM模型名称，默认为"deepseek-v3"
        baseprompt: 基础提示词，用于指导LLM生成图像描述
        prefix: 提示词前缀，会添加到生成的提示词前面
        prompt_cover_image: 封面图像提示词，用于索引为"0"的字幕项
    """
    model: str = DEFAULT_MODEL
    baseprompt: str = ""
    prefix: str = ""
    prompt_cover_image: str = ""


@dataclass
class ImageDescriptionConfig:
    """图像描述生成配置数据类。
    
    封装主入口函数所需的所有配置参数，简化函数签名并提高可维护性。
    
    Attributes:
        srtpath: SRT文件路径
        srtdatapath: 数据JSON文件路径
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        model: 使用的LLM模型名称，默认为"deepseek-v3"
        topic_extra: 主题额外配置，用于选择生成方式
            - 如果generate_type为"none"或空字符串，使用V1方式
            - 否则使用V2方式
    """
    srtpath: str
    srtdatapath: str
    prompt_gen_images: str
    prompt_prefix: str
    prompt_cover_image: str
    model: str = DEFAULT_MODEL
    topic_extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_generator_config(self) -> GeneratorConfig:
        """转换为生成器配置。
        
        Returns:
            生成器配置对象
        """
        return GeneratorConfig(
            model=self.model,
            baseprompt=self.prompt_gen_images,
            prefix=self.prompt_prefix,
            prompt_cover_image=self.prompt_cover_image,
        )
    
    def get_generate_type(self) -> str:
        """获取生成方式类型。
        
        Returns:
            生成方式类型："none"（V1）或其他值（V2）
        """
        return self.topic_extra.get("generate_type", GENERATE_TYPE_V1)
    
    def should_use_v2(self) -> bool:
        """判断是否应该使用V2生成方式。
        
        Returns:
            如果应该使用V2，返回True；否则返回False
        """
        generate_type = self.get_generate_type()
        return generate_type not in ["", GENERATE_TYPE_V1]




