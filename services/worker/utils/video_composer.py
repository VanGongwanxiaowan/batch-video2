"""视频合成模块（添加字幕、Logo等）

代码重构说明：
- 使用 core.utils.ffmpeg.builder 中的 FFmpegCommandBuilder
- 提供便捷函数 build_subtitle_and_logo_command 简化命令构建
"""
import json
import os
from typing import Optional

from utils.video_utils import hex_to_ffmpeg_abgr
from worker.config import settings

from core.logging_config import setup_logging
from core.utils.ffmpeg import FFmpegError, run_ffmpeg, run_ffmpeg_async, FFmpegCore
# 使用 FFmpeg 命令构建器
from core.utils.ffmpeg.builder import (
    build_logo_overlay_command,
    build_subtitle_and_logo_command,
    build_subtitle_command,
)

logger = setup_logging("worker.utils.video_composer")

HUMAN_CONFIG_PATH = settings.human_config_path


def _get_subtitle_style(
    is_horizontal: bool,
    background_hex_color: str,
    account_name: str = "",
) -> str:
    """
    获取字幕样式字符串
    
    Args:
        is_horizontal: 是否为横向视频
        background_hex_color: 背景颜色（十六进制）
        account_name: 账户名称
        
    Returns:
        字幕样式字符串
    """
    background_abgr = hex_to_ffmpeg_abgr(background_hex_color)
    
    with open(HUMAN_CONFIG_PATH, "r", encoding="utf-8") as fp:
        font_config = json.load(fp)['font']
    
    account_config = font_config.get(account_name, {})
    font_name = account_config.get("path") if account_config else None
    fontsize = 40 if is_horizontal else 18
    
    if font_name:
        subtitle_style = (
            f"FontName={font_name},Fontsize={fontsize},Bold=1,"
            f"PrimaryColour=&H000000&,BackSize=100,OutlineColour=&HFFFFFF&,"
            f"BackSize=10,BackColour={background_abgr},BorderStyle=4,Outline=4,"
            f"MarginV=30,WrapStyle=2"
        )
    else:
        subtitle_style = (
            f"Fontsize={fontsize},Bold=1,PrimaryColour=&H000000&,BackSize=100,"
            f"OutlineColour=&HFFFFFF&,BackSize=10,BackColour={background_abgr},"
            f"BorderStyle=4,Outline=4,MarginV=30,WrapStyle=2"
        )
    
    return subtitle_style


async def add_subtitle_to_video(
    srtpath: str,
    audiopath: str,
    combined_video: str,
    subtitled_video: str,
    is_horizontal: bool,
    background_hex_color: str = "#578B2E",
    account_name: str = "",
) -> None:
    """
    为视频添加字幕和音频 (异步)

    Args:
        srtpath: SRT字幕文件路径
        audiopath: 音频文件路径
        combined_video: 输入视频路径
        subtitled_video: 输出视频路径
        is_horizontal: 是否为横向视频
        background_hex_color: 字幕背景颜色
        account_name: 账户名称

    代码重构说明：
        使用 build_subtitle_command 便捷函数构建命令
    """
    subtitle_style = _get_subtitle_style(is_horizontal, background_hex_color, account_name)

    # 使用 FFmpeg 构建器构建命令
    command = build_subtitle_command(
        video_path=combined_video,
        audio_path=audiopath,
        srt_path=srtpath,
        output_path=subtitled_video,
        subtitle_style=subtitle_style,
        crf=23,
        preset="veryfast",
        timeout=600
    )

    try:
        logger.info(f"执行FFmpeg命令（添加字幕）: {' '.join(command)}")
        await run_ffmpeg_async(command, timeout=600)
        logger.info(f"字幕添加成功: {subtitled_video}")
    except FFmpegError as e:
        logger.error(f"字幕添加失败: {e}")
        raise


async def add_logo_to_video(
    subtitled_video: str,
    logoed_video: str,
    logopath: str,
) -> None:
    """
    为视频添加Logo (异步)

    Args:
        subtitled_video: 输入视频路径
        logoed_video: 输出视频路径
        logopath: Logo图片路径

    代码重构说明：
        使用 build_logo_overlay_command 便捷函数构建命令
    """
    # 使用 FFmpeg 构建器构建命令
    command = build_logo_overlay_command(
        video_path=subtitled_video,
        logo_path=logopath,
        output_path=logoed_video,
        position=(10, 10)
    )

    try:
        await run_ffmpeg_async(command, timeout=600)
        logger.info(f"Logo添加成功: {logoed_video}")
    except FFmpegError as e:
        logger.error(f"Logo添加失败: {e}")
        raise


async def add_subtitle_and_logo_to_video(
    srtpath: str,
    audiopath: str,
    combined_video: str,
    subtitled_video_output: str,
    logopath: str,
    is_horizontal: bool,
    background_hex_color: str = "#578B2E",
    account_name: str = "",
) -> None:
    """
    一次性为视频添加字幕和Logo (异步)

    Args:
        srtpath: SRT字幕文件路径
        audiopath: 音频文件路径
        combined_video: 输入视频路径
        subtitled_video_output: 输出视频路径
        logopath: Logo图片路径
        is_horizontal: 是否为横向视频
        background_hex_color: 字幕背景颜色
        account_name: 账户名称

    代码重构说明：
        使用 build_subtitle_and_logo_command 便捷函数构建命令
    """
    subtitle_style = _get_subtitle_style(is_horizontal, background_hex_color, account_name)

    # 使用 FFmpeg 构建器构建命令
    command = build_subtitle_and_logo_command(
        video_path=combined_video,
        audio_path=audiopath,
        srt_path=srtpath,
        logo_path=logopath,
        output_path=subtitled_video_output,
        subtitle_style=subtitle_style,
        logo_position=(30, 10),
        crf=23,
        preset="veryfast"
    )

    try:
        logger.info(f"执行FFmpeg命令（添加字幕和Logo）: {' '.join(command)}")
        await run_ffmpeg_async(command, timeout=600)
        logger.info(f"字幕和Logo添加成功: {subtitled_video_output}")
    except FFmpegError as e:
        logger.error(f"字幕和Logo添加失败: {e}")
        raise

