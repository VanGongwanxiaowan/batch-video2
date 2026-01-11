"""
FFmpeg工具模块
提供安全的FFmpeg命令执行和视频/音频处理功能

代码重构说明：
- 添加了 FFmpegCommandBuilder 用于流式构建 FFmpeg 命令
- 提供便捷函数用于常见操作（添加字幕、Logo 等）
"""
import subprocess
from pathlib import Path
from typing import List, Optional, Union

from .audio_operations import AudioOperations
from .builder import (
    FFmpegCommandBuilder,
    build_concat_command,
    build_logo_overlay_command,
    build_scale_command,
    build_subtitle_and_logo_command,
    build_subtitle_command,
)
from .composite_operations import CompositeOperations
from .core import FFmpegCore, FFmpegError
from .video_operations import VideoOperations

# 创建全局核心实例
_ffmpeg_core = FFmpegCore()

# 创建全局操作实例
video_ops = VideoOperations(_ffmpeg_core)
audio_ops = AudioOperations(_ffmpeg_core)
composite_ops = CompositeOperations(_ffmpeg_core)

# 导出便捷函数
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
    return _ffmpeg_core.run_command(command, timeout, capture_output)


async def run_ffmpeg_async(
    command: List[str],
    timeout: Optional[int] = None,
    capture_output: bool = True
) -> tuple[int, str, str]:
    """
    便捷函数：异步执行FFmpeg命令

    Args:
        command: FFmpeg命令参数列表
        timeout: 超时时间（秒），None使用默认值300
        capture_output: 是否捕获输出

    Returns:
        tuple[int, str, str]: (return_code, stdout, stderr)

    Raises:
        FFmpegError: 执行失败
    """
    return await _ffmpeg_core.run_command_async(command, timeout, capture_output)


def validate_path(
    path: Union[str, Path],
    must_exist: bool = False
) -> Path:
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
    return _ffmpeg_core.validate_path(path, must_exist)


def get_video_duration(video_path: Union[str, Path]) -> float:
    """
    获取视频时长（秒）

    Args:
        video_path: 视频文件路径

    Returns:
        float: 视频时长（秒）
    """
    import json
    from pathlib import Path

    video_path = _ffmpeg_core.validate_path(video_path, must_exist=True)

    command = [
        'ffprobe', '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        str(video_path)
    ]

    result = _ffmpeg_core.run_command(command, capture_output=True)
    data = json.loads(result.stdout)
    duration = float(data['format'].get('duration', 0))

    return duration


__all__ = [
    # 核心类
    'FFmpegCore',
    'FFmpegError',
    # 操作类
    'VideoOperations',
    'AudioOperations',
    'CompositeOperations',
    # 构建器类
    'FFmpegCommandBuilder',
    # 实例
    'video_ops',
    'audio_ops',
    'composite_ops',
    # 核心函数
    'run_ffmpeg',
    'run_ffmpeg_async',
    'validate_path',
    'get_video_duration',
    # 构建器便捷函数
    'build_subtitle_command',
    'build_logo_overlay_command',
    'build_subtitle_and_logo_command',
    'build_concat_command',
    'build_scale_command',
]

