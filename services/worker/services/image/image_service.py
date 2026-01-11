"""图像生成服务"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from gushi import actor_generate, desc2image_gushi, srt2desc_gushi

from core.exceptions import ImageProcessingException, ServiceException
from core.logging_config import setup_logging
from core.utils.exception_handler import handle_service_method_exceptions
from services.base import BaseService

from .image_handlers import ImageActionHandlerFactory

logger = setup_logging("worker.image")


class ImageService(BaseService):
    """图像生成服务，负责图像描述生成和图像生成"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config, logger)
    
    @handle_service_method_exceptions("IMAGE", "generate_image_descriptions")
    async def generate_image_descriptions(
        self,
        srt_path: str,
        data_json_path: str,
        prompt_gen_images: str,
        prompt_prefix: str,
        prompt_cover_image: str,
        model: str = "gemini-2.5-flash",
        topic_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成图像描述（从字幕生成图像提示词）
        
        Args:
            srt_path: 字幕文件路径
            data_json_path: 数据JSON文件路径
            prompt_gen_images: 图像生成提示词
            prompt_prefix: 提示词前缀
            prompt_cover_image: 封面图像提示词
            model: 使用的模型
            topic_extra: 主题额外配置
            
        Returns:
            处理结果字典
        """
        srt2desc_gushi(
            srt_path,
            data_json_path,
            prompt_gen_images,
            prompt_prefix,
            prompt_cover_image,
            model,
            topic_extra or {},
        )
        return {
            "success": True,
            "data_json_path": data_json_path
        }
    
    @handle_service_method_exceptions("IMAGE", "generate_images")
    async def generate_images(
        self,
        base_path: str,
        width: int = 1360,
        height: int = 768,
        loras: Optional[List[Dict[str, Any]]] = None,
        topic_extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成图像
        
        Args:
            base_path: 基础路径
            width: 图像宽度
            height: 图像高度
            loras: LoRA配置列表
            topic_extra: 主题额外配置
            
        Returns:
            处理结果字典
        """
        desc2image_gushi(
            base_path,
            width,
            height,
            loras or [],
            topic_extra or {},
        )
        return {
            "success": True,
            "base_path": base_path
        }
    
    @handle_service_method_exceptions("IMAGE", "generate_actor_images")
    async def generate_actor_images(
        self,
        base_path: str,
        content: str,
        loras: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        生成Actor图像（相同角色图像）
        
        Args:
            base_path: 基础路径
            content: 内容文本
            loras: LoRA配置列表
            
        Returns:
            处理结果字典
        """
        actor_generate(base_path, content, loras or [])
        return {
            "success": True,
            "base_path": base_path
        }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理图像生成请求（使用策略模式）
        
        Args:
            data: 包含图像生成参数的字典
            
        Returns:
            处理结果字典
        """
        action = data.get("action")
        
        # 使用策略模式获取对应的处理器
        handler = ImageActionHandlerFactory.get_handler(action)
        if handler:
            return await handler.handle(self, data)
        else:
            return {
                "success": False,
                "error": f"未知的操作: {action}"
            }

