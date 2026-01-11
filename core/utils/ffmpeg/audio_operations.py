"""
FFmpeg音频操作模块
提供音频裁剪、格式转换等操作
"""
from pathlib import Path
from typing import Union

from core.exceptions import FFmpegError
from core.logging_config import setup_logging

from .core import FFmpegCore

logger = setup_logging("core.utils.ffmpeg.audio_operations")


class AudioOperations:
    """音频操作类"""
    
    def __init__(self, ffmpeg_core: FFmpegCore) -> None:
        """
        初始化音频操作
        
        Args:
            ffmpeg_core: FFmpeg核心工具实例
        """
        self.core = ffmpeg_core
    
    def cut_audio(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        duration: float,
        start_time: float = 0
    ) -> Path:
        """
        截取音频片段
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            duration: 截取时长(秒)
            start_time: 开始时间(秒)
            
        Returns:
            Path: 输出文件路径
        """
        input_path = self.core.validate_path(input_path, must_exist=True)
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        command = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-ss', str(start_time),
            '-t', str(duration),
            '-acodec', 'copy',
            str(output_path)
        ]
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path
    
    def convert_audio_format(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        codec: str = 'libmp3lame'
    ) -> Path:
        """
        转换音频格式
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            codec: 音频编码器
            
        Returns:
            Path: 输出文件路径
        """
        input_path = self.core.validate_path(input_path, must_exist=True)
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        command = [
            'ffmpeg', '-y',
            '-i', str(input_path),
            '-acodec', codec,
            str(output_path)
        ]
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path

