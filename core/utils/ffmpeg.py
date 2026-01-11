"""
[LEGACY MODULE] 安全的FFmpeg工具类
此模块已被重构为多个专门的模块，位于 core.utils.ffmpeg 包中。

为了保持向后兼容，此文件保留原有类接口，但内部调用新的模块化实现。

新模块结构：
- core.utils.ffmpeg.core: FFmpeg核心工具类
- core.utils.ffmpeg.video_operations: 视频操作
- core.utils.ffmpeg.audio_operations: 音频操作
- core.utils.ffmpeg.composite_operations: 合成操作

建议新代码直接使用新模块，而不是此legacy模块。
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Union

from core.exceptions import FileException, ServiceException
from core.logging_config import setup_logging

# 延迟导入以避免循环导入
logger = setup_logging("core.utils.ffmpeg")


class FFmpegError(ServiceException):
    """FFmpeg执行错误"""
    pass


# 向后兼容：创建FFmpegUtils类包装器
class FFmpegUtils:
    """安全的FFmpeg工具类（向后兼容包装器）"""
    
    def __init__(self, timeout: int = 300):
        """
        初始化FFmpeg工具
        
        Args:
            timeout: 命令执行超时时间(秒)
        """
        # 延迟导入以避免循环导入
        from core.utils.ffmpeg.audio_operations import AudioOperations
        from core.utils.ffmpeg.composite_operations import CompositeOperations
        from core.utils.ffmpeg.core import FFmpegCore
        from core.utils.ffmpeg.video_operations import VideoOperations
        
        self._core = FFmpegCore(timeout)
        self._video_ops = VideoOperations(self._core)
        self._audio_ops = AudioOperations(self._core)
        self._composite_ops = CompositeOperations(self._core)
        self.timeout = timeout
    
    def _validate_path(self, path: Union[str, Path]) -> Path:
        """验证文件路径"""
        return self._core.validate_path(path)
    
    def _run_command(self, command: List[str]) -> None:
        """安全执行FFmpeg命令"""
        self._core.run_command(command)
    
    def cut_audio(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        duration: float,
        start_time: float = 0
    ) -> Path:
        """截取音频片段"""
        return self._audio_ops.cut_audio(input_path, output_path, duration, start_time)
    
    def cut_video(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        start_time: float,
        duration: Optional[float] = None
    ) -> Path:
        """截取视频片段"""
        return self._video_ops.cut_video(input_path, output_path, start_time, duration)
    
    def convert_audio_format(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        codec: str = 'libmp3lame'
    ) -> Path:
        """转换音频格式"""
        return self._audio_ops.convert_audio_format(input_path, output_path, codec)
    
    def scale_video(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        width: int,
        height: int,
        remove_audio: bool = False
    ) -> Path:
        """缩放视频"""
        return self._video_ops.scale_video(input_path, output_path, width, height, remove_audio)
    
    def concat_videos(
        self,
        video_paths: List[Union[str, Path]],
        output_path: Union[str, Path]
    ) -> Path:
        """合并多个视频文件"""
        return self._video_ops.concat_videos(video_paths, output_path)
    
    def add_logo(
        self,
        video_path: Union[str, Path],
        logo_path: Union[str, Path],
        output_path: Union[str, Path],
        position: str = "30:10"
    ) -> Path:
        """为视频添加Logo"""
        return self._video_ops.add_logo(video_path, logo_path, output_path, position)
    
    def combine_video_audio(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        video_filters: Optional[str] = None
    ) -> Path:
        """合并视频和音频"""
        return self._composite_ops.combine_video_audio(
            video_path, audio_path, output_path, video_filters
        )


# 创建全局实例
ffmpeg_utils = FFmpegUtils()


def run_ffmpeg(
    command: List[str],
    timeout: Optional[int] = None,
    capture_output: bool = True
) -> subprocess.CompletedProcess:
    """
    便捷函数：执行FFmpeg命令
    
    Args:
        command: FFmpeg命令参数列表
        timeout: 超时时间（秒），None使用默认值300
        capture_output: 是否捕获输出
        
    Returns:
        subprocess.CompletedProcess: 执行结果
        
    Raises:
        FFmpegError: 执行失败
    """
    from core.utils.ffmpeg import run_ffmpeg as _run_ffmpeg
    return _run_ffmpeg(command, timeout, capture_output)


def validate_path(path: Union[str, Path], must_exist: bool = False) -> Path:
    """
    便捷函数：验证文件路径
    
    Args:
        path: 文件路径
        must_exist: 是否必须存在
        
    Returns:
        Path: 验证后的路径对象
        
    Raises:
        FileException: 路径验证失败
    """
    from core.utils.ffmpeg import validate_path as _validate_path
    return _validate_path(path, must_exist)


def get_video_duration(video_path: Union[str, Path]) -> float:
    """
    便捷函数：获取视频时长（秒）
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        float: 视频时长（秒）
    """
    from core.utils.ffmpeg import get_video_duration as _get_video_duration
    return _get_video_duration(video_path)
