"""
FFmpeg视频操作模块
提供视频裁剪、缩放、合并等操作
"""
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from core.exceptions import FFmpegError, FileException
from core.logging_config import setup_logging

from .core import FFmpegCore

logger = setup_logging("core.utils.ffmpeg.video_operations")


class VideoOperations:
    """视频操作类"""
    
    def __init__(self, ffmpeg_core: FFmpegCore) -> None:
        """
        初始化视频操作
        
        Args:
            ffmpeg_core: FFmpeg核心工具实例
        """
        self.core = ffmpeg_core
    
    def cut_video(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        start_time: float,
        duration: Optional[float] = None
    ) -> Path:
        """
        截取视频片段
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出视频文件路径
            start_time: 开始时间(秒)
            duration: 截取时长(秒)，None表示到结尾
            
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
            '-ss', str(start_time)
        ]
        
        if duration is not None:
            command.extend(['-t', str(duration)])
        
        command.extend(['-c', 'copy', str(output_path)])
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path
    
    def scale_video(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        width: int,
        height: int,
        remove_audio: bool = False
    ) -> Path:
        """
        缩放视频
        
        Args:
            input_path: 输入视频文件路径
            output_path: 输出视频文件路径
            width: 目标宽度
            height: 目标高度
            remove_audio: 是否移除音频
            
        Returns:
            Path: 输出文件路径
        """
        input_path = self.core.validate_path(input_path, must_exist=True)
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        command = [
            'ffmpeg', '-y',
            '-i', str(input_path)
        ]
        
        if remove_audio:
            command.append('-an')
        
        command.extend([
            '-r', '30',
            '-pix_fmt', 'yuv420p',
            '-vf', f'scale={width}:{height}:flags=lanczos,setsar=1',
            str(output_path)
        ])
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path
    
    def concat_videos(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path]
    ) -> Path:
        """
        合并多个视频文件
        
        Args:
            video_paths: 视频文件路径列表
            output_path: 输出视频文件路径
            
        Returns:
            Path: 输出文件路径
        """
        if not video_paths:
            raise ValueError("Video paths list cannot be empty")
        
        # 验证所有输入路径
        validated_paths = []
        for path in video_paths:
            validated_path = self.core.validate_path(path, must_exist=True)
            validated_paths.append(validated_path)
        
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
            for path in validated_paths:
                temp_file.write(f"file '{path.absolute()}'\n")
            temp_file_path = temp_file.name
        
        try:
            command = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', temp_file_path,
                '-c', 'copy',
                str(output_path)
            ]
            
            self.core.run_command(command)
            
            if not output_path.exists():
                raise FFmpegError(f"Output file was not created: {output_path}")
            
            return output_path
            
        finally:
            # 清理临时文件
            Path(temp_file_path).unlink(missing_ok=True)
    
    def add_logo(
        self,
        video_path: Union[str, Path],
        logo_path: Union[str, Path],
        output_path: Union[str, Path],
        position: str = "30:10"
    ) -> Path:
        """
        为视频添加Logo
        
        Args:
            video_path: 视频文件路径
            logo_path: Logo文件路径
            output_path: 输出视频文件路径
            position: Logo位置 (x:y)
            
        Returns:
            Path: 输出文件路径
        """
        video_path = self.core.validate_path(video_path, must_exist=True)
        logo_path = self.core.validate_path(logo_path, must_exist=True)
        output_path = self.core.validate_path(output_path)
        
        # 确保输出目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        command = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-i', str(logo_path),
            '-filter_complex', f'[1:v]format=rgba[ol];[0:v][ol]overlay={position}',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        self.core.run_command(command)
        
        if not output_path.exists():
            raise FFmpegError(f"Output file was not created: {output_path}")
        
        return output_path

