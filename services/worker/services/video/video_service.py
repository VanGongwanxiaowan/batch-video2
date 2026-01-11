"""视频处理服务"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from gushi import (
    concat_videos,
    concat_videos_with_transitions,
    generate_video,
    h2v,
    videocombine,
    videocombineallwithlogo,
)

from core.exceptions import FFmpegError, ServiceException
from core.logging_config import setup_logging
from services.base import BaseService

from .video_handlers import VideoActionHandlerFactory

logger = setup_logging("worker.video")


class VideoService(BaseService):
    """视频处理服务，负责动效生成、视频合并等"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config, logger)
    
    async def create_scene_videos(
        self,
        srt_path: str,
        width: int = 1360,
        height: int = 768,
        over: int = 0,
    ) -> Dict[str, Any]:
        """
        创建分镜视频（从图片生成带动效的视频）
        
        Args:
            srt_path: 字幕文件路径
            width: 视频宽度
            height: 视频高度
            over: 额外时长（秒）
            
        Returns:
            处理结果字典
        """
        try:
            generate_video(srt_path, width, height, over)
            return {
                "success": True,
                "message": "分镜视频生成完成"
            }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            self.logger.error(f"[create_scene_videos] 文件操作失败: {e}", exc_info=True)
            return self.handle_error(e)
        except FFmpegError as e:
            # FFmpeg处理错误
            self.logger.error(f"[create_scene_videos] FFmpeg处理失败: {e}", exc_info=True)
            return self.handle_error(ServiceException(f"视频生成服务错误: {e}"))
        except Exception as e:
            # 其他异常（视频生成服务错误等）
            self.logger.error(f"[create_scene_videos] 视频生成失败: {e}", exc_info=True)
            return self.handle_error(e)
    
    async def concat_scene_videos(
        self,
        srt_path: str,
        base_path: str,
        enable_transition: bool = False,
        transition_types: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        合并分镜视频
        
        Args:
            srt_path: 字幕文件路径
            base_path: 基础路径
            enable_transition: 是否启用转场效果
            transition_types: 转场类型列表
            
        Returns:
            合并后的视频路径，失败返回None
        """
        try:
            if enable_transition:
                transition_types = transition_types or ["fade"]
                return await concat_videos_with_transitions(srt_path, base_path, transition_types)
            else:
                return await concat_videos(srt_path, base_path)
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            self.logger.error(f"[concat_scene_videos] 文件操作失败: {e}", exc_info=True)
            return None
        except FFmpegError as e:
            # FFmpeg处理错误
            self.logger.error(f"[concat_scene_videos] FFmpeg处理失败: {e}", exc_info=True)
            return None
        except Exception as e:
            # 其他异常（视频处理错误等）
            self.logger.error(f"[concat_scene_videos] 合并视频失败: {e}", exc_info=True)
            return None
    
    async def add_subtitle_and_audio(
        self,
        srt_path: str,
        audio_path: str,
        combined_video: str,
        output_video: str,
        is_horizontal: bool = True,
        background_hex_color: str = "#578B2E",
        account_name: str = "",
    ) -> Dict[str, Any]:
        """
        添加字幕和音频到视频
        
        Args:
            srt_path: 字幕文件路径
            audio_path: 音频文件路径
            combined_video: 合并后的视频路径
            output_video: 输出视频路径
            is_horizontal: 是否为横向视频
            background_hex_color: 字幕背景颜色
            account_name: 账户名称
            
        Returns:
            处理结果字典
        """
        try:
            await videocombine(
                srt_path,
                audio_path,
                combined_video,
                output_video,
                is_horizontal,
                background_hex_color,
                account_name,
            )
            return {
                "success": True,
                "video_path": output_video
            }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            self.logger.error(f"[add_subtitle_and_audio] 文件操作失败: {e}", exc_info=True)
            return self.handle_error(e)
        except FFmpegError as e:
            # FFmpeg处理错误
            self.logger.error(f"[add_subtitle_and_audio] FFmpeg处理失败: {e}", exc_info=True)
            return self.handle_error(ServiceException(f"视频处理服务错误: {e}"))
        except Exception as e:
            # 其他异常（视频处理错误等）
            self.logger.error(f"[add_subtitle_and_audio] 视频处理失败: {e}", exc_info=True)
            return self.handle_error(e)
    
    async def add_logo(
        self,
        srt_path: str,
        audio_path: str,
        combined_video: str,
        output_video: str,
        logo_path: str,
        is_horizontal: bool = True,
        background_hex_color: str = "#578B2E",
        account_name: str = "",
    ) -> Dict[str, Any]:
        """
        添加Logo到视频
        
        Args:
            srt_path: 字幕文件路径
            audio_path: 音频文件路径
            combined_video: 合并后的视频路径
            output_video: 输出视频路径
            logo_path: Logo文件路径
            is_horizontal: 是否为横向视频
            background_hex_color: 字幕背景颜色
            account_name: 账户名称
            
        Returns:
            处理结果字典
        """
        try:
            await videocombineallwithlogo(
                srt_path,
                audio_path,
                combined_video,
                output_video,
                logo_path,
                is_horizontal,
                background_hex_color,
                account_name,
            )
            return {
                "success": True,
                "video_path": output_video
            }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            self.logger.error(f"[add_logo] 文件操作失败: {e}", exc_info=True)
            return self.handle_error(e)
        except FFmpegError as e:
            # FFmpeg处理错误
            self.logger.error(f"[add_logo] FFmpeg处理失败: {e}", exc_info=True)
            return self.handle_error(ServiceException(f"视频处理服务错误: {e}"))
        except Exception as e:
            # 其他异常（视频处理错误等）
            self.logger.error(f"[add_logo] 视频处理失败: {e}", exc_info=True)
            return self.handle_error(e)
    
    async def convert_h2v(
        self,
        index_text: str,
        title_text: str,
        desc_text: str,
        audio: str,
        input_path: str,
        output_path: str,
    ) -> Dict[str, Any]:
        """
        横屏转竖屏（H2V）
        
        Args:
            index_text: 索引文本
            title_text: 标题文本
            desc_text: 描述文本
            audio: 背景音频文件名
            input_path: 输入视频路径
            output_path: 输出视频路径
            
        Returns:
            处理结果字典
        """
        try:
            h2v(index_text, title_text, desc_text, audio, input_path, output_path)
            return {
                "success": True,
                "video_path": output_path
            }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            self.logger.error(f"[convert_h2v] 文件操作失败: {e}", exc_info=True)
            return self.handle_error(e)
        except FFmpegError as e:
            # FFmpeg处理错误
            self.logger.error(f"[convert_h2v] FFmpeg处理失败: {e}", exc_info=True)
            return self.handle_error(ServiceException(f"视频处理服务错误: {e}"))
        except Exception as e:
            # 其他异常（视频处理错误等）
            self.logger.error(f"[convert_h2v] 视频处理失败: {e}", exc_info=True)
            return self.handle_error(e)
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理视频请求（使用策略模式）
        
        Args:
            data: 包含视频处理参数的字典
            
        Returns:
            处理结果字典
        """
        action = data.get("action")
        
        # 使用策略模式获取对应的处理器
        handler = VideoActionHandlerFactory.get_handler(action)
        if handler:
            return await handler.handle(self, data)
        else:
            return {
                "success": False,
                "error": f"未知的操作: {action}"
            }

