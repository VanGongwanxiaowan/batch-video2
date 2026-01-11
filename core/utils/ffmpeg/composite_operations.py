"""
FFmpeg合成操作模块
提供视频和音频合成等操作
"""
from pathlib import Path
from typing import Optional, Union

from core.exceptions import FFmpegError, FileException
from core.logging_config import setup_logging

from .core import FFmpegCore

logger = setup_logging("core.utils.ffmpeg.composite_operations")


class CompositeOperations:
    """合成操作类"""
    
    def __init__(self, ffmpeg_core: FFmpegCore) -> None:
        """
        初始化合成操作
        
        Args:
            ffmpeg_core: FFmpeg核心工具实例
        """
        self.core = ffmpeg_core
    
    def combine_video_audio(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        video_filters: Optional[str] = None
    ) -> Path:
        """
        合并视频和音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出文件路径
            video_filters: 视频滤镜
            
        Returns:
            Path: 输出文件路径
        """
        video_path = self.core.validate_path(video_path, must_exist=True)
        audio_path = self.core.validate_path(audio_path, must_exist=True)
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        command = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(audio_path)
        ]
        
        if video_filters:
            command.extend(['-vf', video_filters])
        
        command.extend([
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'veryfast',
            '-c:a', 'copy',
            '-map', '0:v',
            '-map', '1:a',
            '-shortest',
            str(output_path)
        ])
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path

