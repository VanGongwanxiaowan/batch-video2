"""视频服务操作处理器

使用策略模式，将不同的视频操作封装为独立的处理器类。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.logging_config import setup_logging

logger = setup_logging("worker.video.handlers")


class VideoActionHandler(ABC):
    """视频操作处理器基类"""
    
    @abstractmethod
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频操作
        
        Args:
            service: VideoService 实例
            data: 操作数据字典
            
        Returns:
            处理结果字典
        """
        pass


class CreateSceneVideosHandler(VideoActionHandler):
    """创建分镜视频处理器"""
    
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.create_scene_videos(
            srt_path=data.get("srt_path", ""),
            width=data.get("width", 1360),
            height=data.get("height", 768),
            over=data.get("over", 0),
        )


class ConcatVideosHandler(VideoActionHandler):
    """合并视频处理器"""
    
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        video_path = await service.concat_scene_videos(
            srt_path=data.get("srt_path", ""),
            base_path=data.get("base_path", ""),
            enable_transition=data.get("enable_transition", False),
            transition_types=data.get("transition_types"),
        )
        return {
            "success": True,
            "video_path": video_path
        }


class AddSubtitleHandler(VideoActionHandler):
    """添加字幕处理器"""
    
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.add_subtitle_and_audio(
            srt_path=data.get("srt_path", ""),
            audio_path=data.get("audio_path", ""),
            combined_video=data.get("combined_video", ""),
            output_video=data.get("output_video", ""),
            is_horizontal=data.get("is_horizontal", True),
            background_hex_color=data.get("background_hex_color", "#578B2E"),
            account_name=data.get("account_name", ""),
        )


class AddLogoHandler(VideoActionHandler):
    """添加Logo处理器"""
    
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.add_logo(
            srt_path=data.get("srt_path", ""),
            audio_path=data.get("audio_path", ""),
            combined_video=data.get("combined_video", ""),
            output_video=data.get("output_video", ""),
            logo_path=data.get("logo_path", ""),
            is_horizontal=data.get("is_horizontal", True),
            background_hex_color=data.get("background_hex_color", "#578B2E"),
            account_name=data.get("account_name", ""),
        )


class H2VHandler(VideoActionHandler):
    """横屏转竖屏处理器"""
    
    async def handle(self, service: 'VideoService', data: Dict[str, Any]) -> Dict[str, Any]:
        return await service.convert_h2v(
            index_text=data.get("index_text", ""),
            title_text=data.get("title_text", ""),
            desc_text=data.get("desc_text", ""),
            audio=data.get("audio", ""),
            input_path=data.get("input_path", ""),
            output_path=data.get("output_path", ""),
        )


class VideoActionHandlerFactory:
    """视频操作处理器工厂"""
    
    _handlers = {
        "create_scene_videos": CreateSceneVideosHandler(),
        "concat_videos": ConcatVideosHandler(),
        "add_subtitle": AddSubtitleHandler(),
        "add_logo": AddLogoHandler(),
        "h2v": H2VHandler(),
    }
    
    @classmethod
    def get_handler(cls, action: str) -> Optional[VideoActionHandler]:
        """
        获取对应的处理器
        
        Args:
            action: 操作名称
            
        Returns:
            处理器实例，如果不存在返回None
        """
        return cls._handlers.get(action)
    
    @classmethod
    def register_handler(cls, action: str, handler: VideoActionHandler) -> None:
        """
        注册新的处理器
        
        Args:
            action: 操作名称
            handler: 处理器实例
        """
        cls._handlers[action] = handler

