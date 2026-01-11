"""图像服务操作处理器

使用策略模式，将不同的图像操作封装为独立的处理器类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.logging_config import setup_logging

logger = setup_logging("worker.image.handlers")


class ImageActionHandler(ABC):
    """图像操作处理器基类"""
    
    @abstractmethod
    async def handle(self, service: 'ImageService', data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图像操作
        
        Args:
            service: ImageService 实例
            data: 操作数据字典
            
        Returns:
            处理结果字典
        """
        pass


class GenerateDescriptionsHandler(ImageActionHandler):
    """生成图像描述处理器"""
    
    async def handle(self, service: 'ImageService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.generate_image_descriptions(
            srt_path=data.get("srt_path", ""),
            data_json_path=data.get("data_json_path", ""),
            prompt_gen_images=data.get("prompt_gen_images", ""),
            prompt_prefix=data.get("prompt_prefix", ""),
            prompt_cover_image=data.get("prompt_cover_image", ""),
            model=data.get("model", "gemini-2.5-flash"),
            topic_extra=data.get("topic_extra"),
        )


class GenerateImagesHandler(ImageActionHandler):
    """生成图像处理器"""
    
    async def handle(self, service: 'ImageService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.generate_images(
            base_path=data.get("base_path", ""),
            width=data.get("width", 1360),
            height=data.get("height", 768),
            loras=data.get("loras"),
            topic_extra=data.get("topic_extra"),
        )


class GenerateActorHandler(ImageActionHandler):
    """生成Actor图像处理器"""
    
    async def handle(self, service: 'ImageService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.generate_actor_images(
            base_path=data.get("base_path", ""),
            content=data.get("content", ""),
            loras=data.get("loras"),
        )


class ImageActionHandlerFactory:
    """图像操作处理器工厂"""
    
    _handlers = {
        "generate_descriptions": GenerateDescriptionsHandler(),
        "generate_images": GenerateImagesHandler(),
        "generate_actor": GenerateActorHandler(),
    }
    
    @classmethod
    def get_handler(cls, action: str) -> Optional[ImageActionHandler]:
        """
        获取对应的处理器
        
        Args:
            action: 操作名称
            
        Returns:
            处理器实例，如果不存在返回None
        """
        return cls._handlers.get(action)
    
    @classmethod
    def register_handler(cls, action: str, handler: ImageActionHandler) -> None:
        """
        注册新的处理器
        
        Args:
            action: 操作名称
            handler: 处理器实例
        """
        cls._handlers[action] = handler

