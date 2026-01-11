"""图像描述生成器基类

定义图像描述生成器的通用接口和共享逻辑。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.image_description.base_generator")


class ImageDescriptionGenerator(ABC):
    """图像描述生成器抽象基类。
    
    所有图像描述生成器都应该继承此类并实现generate方法。
    """
    
    def __init__(
        self,
        model: str,
        baseprompt: str,
        prefix: str,
        prompt_cover_image: str,
    ) -> None:
        """初始化生成器。
        
        Args:
            model: 使用的LLM模型名称
            baseprompt: 基础提示词
            prefix: 提示词前缀
            prompt_cover_image: 封面图像提示词
        """
        self.model = model
        self.baseprompt = baseprompt
        self.prefix = prefix
        self.prompt_cover_image = prompt_cover_image
    
    @abstractmethod
    def generate(
        self,
        srtdata: Dict[str, Dict[str, Any]],
        basepath: str,
    ) -> Dict[str, Dict[str, Any]]:
        """生成图像描述。
        
        Args:
            srtdata: 字幕数据字典，格式为 {key: {"text": str, "prompt": str, ...}}
            basepath: 基础路径，用于检查图像文件是否存在
            
        Returns:
            更新后的字幕数据字典，prompt字段已填充
            
        Raises:
            Exception: 如果生成失败
        """
        pass
    
    def apply_cover_image_prompt(
        self,
        srtdata: Dict[str, Dict[str, Any]],
    ) -> None:
        """应用封面图像提示词。
        
        如果配置了封面图像提示词，将其应用到索引为"0"的字幕项。
        
        Args:
            srtdata: 字幕数据字典（会被修改）
        """
        if self.prompt_cover_image.strip() and "0" in srtdata:
            srtdata["0"]["prompt"] = self.prompt_cover_image
            srtdata["0"]["is_actor"] = True
            logger.debug("已应用封面图像提示词")

