"""视频处理工具函数"""
from pathlib import Path
from typing import Union

from core.logging_config import setup_logging
from core.utils.ffmpeg import get_video_duration as safe_get_video_duration
from core.utils.ffmpeg import (
    validate_path,
)

logger = setup_logging("worker.utils.video_utils")


def get_video_duration(video_path: Union[str, Path]) -> float:
    """获取视频精确时长（秒）"""
    return safe_get_video_duration(video_path)


def hex_to_ffmpeg_abgr(hex_color: str) -> str:
    """
    将Web十六进制颜色代码（#RRGGBB）转换为FFmpeg ABGR格式（&HAA BB GG RR&）。
    默认Alpha通道为40（25%不透明度）。
    
    Args:
        hex_color: 十六进制颜色代码，如 "#FF0000"
        
    Returns:
        FFmpeg ABGR格式颜色字符串
        
    Raises:
        ValueError: 如果颜色格式无效
    """
    if not hex_color.startswith("#") or len(hex_color) != 7:
        raise ValueError("Invalid hex color format. Expected #RRGGBB.")

    hex_color = hex_color[1:]  # 移除 #
    r = hex_color[0:2]
    g = hex_color[2:4]
    b = hex_color[4:6]

    # FFmpeg ABGR 格式通常使用 &HAA BB GG RR&
    # 默认 Alpha 值为 40 (25% 不透明度)，如果需要完全不透明，可以使用 FF
    alpha = "40"  # 示例中是40，所以这里也用40

    # 转换为 ABGR 顺序
    ffmpeg_abgr = f"&H{alpha}{b}{g}{r}&"
    return ffmpeg_abgr

