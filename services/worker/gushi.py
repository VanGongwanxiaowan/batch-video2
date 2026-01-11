"""
[LEGACY MODULE] 此模块已被重构为多个专门的模块。

为了保持向后兼容，此文件保留原有函数接口，但内部调用新的模块化实现。

新模块结构：
- utils.srt_processor: 字幕数据处理
- utils.image_description_generator: 图像描述生成
- utils.image_generator: 图像生成
- utils.video_processor: 视频处理
- utils.video_combiner: 视频合并
- utils.video_composer: 视频合成（字幕、Logo）
- utils.video_utils: 视频工具函数

建议新代码直接使用新模块，而不是此legacy模块。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 使用 FFmpegCommandBuilder 构建命令
- 替换硬编码的 1360x768 默认分辨率
"""
import json
import os
import random
from typing import Any, Dict, List, Optional

import pysrt
from utils.image_description_generator import generate_image_descriptions
from utils.image_generator import (
    generate_actor_image,
    generate_images_from_srtdata,
)
from utils.srt_processor import load_srtdata as _load_srtdata
from utils.video_combiner import concat_videos, concat_videos_with_transitions
from utils.video_composer import (
    add_logo_to_video,
    add_subtitle_and_logo_to_video,
    add_subtitle_to_video,
)
from utils.video_processor import compare_video
from utils.video_processor import is_video_corrupted as is_video_corrupted_opencv

# 导入新的模块化实现
from utils.video_utils import get_video_duration, hex_to_ffmpeg_abgr

from core.logging_config import setup_logging
from core.utils.ffmpeg import (
    FFmpegError,
    run_ffmpeg,
    validate_path,
)
# 使用 FFmpeg 命令构建器
from core.utils.ffmpeg.builder import FFmpegCommandBuilder
# 使用统一的视频配置
from core.config.video_config import VideoResolution, get_dimensions

logger = setup_logging("worker.gushi")

from worker.config import settings

# 默认分辨率（使用统一配置）
DEFAULT_WIDTH, DEFAULT_HEIGHT = get_dimensions(is_horizontal=True)

HUMAN_CONFIG_PATH = settings.human_config_path
BG_AUDIO_DIR = settings.bg_audio_dir
FONT_DIR = settings.font_dir


def random_bool(l: float, r: float) -> bool:
    """随机布尔值
    
    Args:
        l: 左侧值
        r: 右侧值
        
    Returns:
        bool: 随机布尔值
    """
    return random.random() < l / (l + r)


def load_srtdata_gushi(srtpath: str) -> Dict[str, Dict[str, Any]]:
    """[LEGACY] 加载字幕数据，内部调用新模块
    
    Args:
        srtpath: 字幕文件路径
        
    Returns:
        Dict[str, Dict[str, Any]]: 字幕数据字典
    """
    return _load_srtdata(srtpath)


# [LEGACY] 这些函数已被重构到 utils.image_description_generator 模块
# 保留函数签名以保持向后兼容，但内部调用新实现
def srt2desc_chat_gushi_v2(
    srtdata: Dict[str, Dict[str, Any]], 
    basepath: str, 
    model: str, 
    baseprompt: str, 
    prefix: str, 
    prompt_cover_image: str
) -> Dict[str, Dict[str, Any]]:
    """[LEGACY] 使用v2方法生成图像描述
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        model: 模型名称
        baseprompt: 基础提示词
        prefix: 前缀
        prompt_cover_image: 封面图像提示词
        
    Returns:
        Dict[str, Dict[str, Any]]: 更新后的字幕数据字典
    """
    from utils.image_description_generator import generate_descriptions_v2
    return generate_descriptions_v2(srtdata, basepath, model, baseprompt, prefix, prompt_cover_image)


def srt2desc_chat_gushi(
    srtdata: Dict[str, Dict[str, Any]], 
    basepath: str, 
    model: str, 
    baseprompt: str, 
    prefix: str, 
    prompt_cover_image: str
) -> Dict[str, Dict[str, Any]]:
    """[LEGACY] 使用v1方法生成图像描述
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        model: 模型名称
        baseprompt: 基础提示词
        prefix: 前缀
        prompt_cover_image: 封面图像提示词
        
    Returns:
        Dict[str, Dict[str, Any]]: 更新后的字幕数据字典
    """
    from utils.image_description_generator import generate_descriptions_v1
    return generate_descriptions_v1(srtdata, basepath, model, baseprompt, prefix, prompt_cover_image)


def srt2desc_gushi(
    srtpath: str,
    srtdatapath: str,
    prompt_gen_images: str,
    prompt_prefix: str,
    prompt_cover_image: str,
    model: str = "deepseek-v3",
    topic_extra: Dict[str, Any] = {},
) -> None:
    """[LEGACY] 生成图像描述，内部调用新模块
    
    Args:
        srtpath: 字幕文件路径
        srtdatapath: 数据文件路径
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        model: 模型名称
        topic_extra: 主题额外配置
    """
    return generate_image_descriptions(
        srtpath, srtdatapath, prompt_gen_images, prompt_prefix,
        prompt_cover_image, model, topic_extra
    )


# compare_video 已迁移到 utils.video_processor，直接使用导入的函数


def saveimage(
    srtdata: Dict[str, Dict[str, Any]],
    basepath: str = "",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    loras: List[Dict[str, Any]] = [],
    topic_extra: Dict[str, Any] = {},
) -> None:
    """[LEGACY] 生成图像，内部调用新模块
    
    Args:
        srtdata: 字幕数据字典
        basepath: 基础路径
        width: 图像宽度
        height: 图像高度
        loras: LoRA配置列表
        topic_extra: 主题额外配置
    """
    return generate_images_from_srtdata(srtdata, basepath, width, height, loras, topic_extra)


def h2v(
    index_text: str,
    title_text: str,
    desc_text: str,
    audio: str,
    input_path: str,
    output_path: str
) -> None:
    """
    [LEGACY] 将横向视频转换为竖向视频，添加文字和背景音乐

    此函数保留仅用于向后兼容，建议使用新的模块化实现。

    代码重构说明：
        使用 FFmpegCommandBuilder 构建命令
    """
    # 使用统一的视频配置获取分辨率
    landscape_width, landscape_height = get_dimensions(is_horizontal=True)
    # 竖向高度 = 横向高度 * 3 + 文字空间
    portrait_total_height = landscape_height * 3 + 114

    volume_factor_bg_audio = 0.08  # 背景音乐音量
    volume_factor_original_audio = 1.0  # 原始视频音量 (1.0表示不变)
    audiobasepath = str(BG_AUDIO_DIR)
    fontpath = str(FONT_DIR / "方正粗谭黑简体.ttf")
    audiofilepath = os.path.join(audiobasepath, audio) if audio else None
    audiofiles = []

    # 检查背景音频目录是否存在
    if audio and audiofilepath and os.path.exists(audiofilepath):
        audiofiles = os.listdir(audiofilepath)

    if audiofiles:
        # 有背景音乐的情况
        audiopath = random.choice(audiofiles)
        audiofile = os.path.join(audiofilepath, audiopath)

        # 构建filter_complex字符串（使用配置的分辨率）
        filter_complex = (
            f"[0:v]pad=width={landscape_width}:height={portrait_total_height}:x=0:y=(oh-ih)/2:color=black,"
            f"drawtext=fontfile={fontpath}:text='{desc_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=1800,"
            f"drawtext=fontfile={fontpath}:text='{index_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=400,"
            f"drawtext=fontfile={fontpath}:text='{title_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=600[v];"
            f"[0:a]volume={volume_factor_original_audio}[a0];"
            f"[1:a]volume={volume_factor_bg_audio},aloop=loop=-1:size=2e9[a1];"
            f"[a0][a1]amix=inputs=2:duration=shortest[a]"
        )

        try:
            # 使用 FFmpegCommandBuilder 构建命令
            command = (FFmpegCommandBuilder()
                       .add_input(str(validate_path(input_path, must_exist=True)))
                       .add_input(str(validate_path(audiofile, must_exist=True)))
                       .add_option("filter_complex", filter_complex)
                       .map_stream("[v]")
                       .map_stream("[a]")
                       .set_video_codec("libx264")
                       .set_quality(crf=23, preset="veryfast")
                       .set_audio_codec("aac")
                       .add_option("b:a", "192k")
                       .add_option("shortest", "")
                       .set_output(str(validate_path(output_path)))
                       .build())

            run_ffmpeg(command, timeout=300)
            logger.info(f"Successfully processed video with background audio: {output_path}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except FFmpegError as e:
            # 其他异常（视频处理错误等）
            logger.error(f"[h2v] Failed to process video with background audio: {e}", exc_info=True)
            raise
    else:
        # 只保留原音频的情况
        filter_complex = (
            f"[0:v]pad=width={landscape_width}:height={portrait_total_height}:x=0:y=(oh-ih)/2:color=black,"
            f"drawtext=fontfile={fontpath}:text='{desc_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=1800,"
            f"drawtext=fontfile={fontpath}:text='{index_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=400,"
            f"drawtext=fontfile={fontpath}:text='{title_text}':fontcolor=white:fontsize=120:x=(w-text_w)/2:y=600[v]"
        )

        try:
            # 使用 FFmpegCommandBuilder 构建命令
            command = (FFmpegCommandBuilder()
                       .add_input(str(validate_path(input_path, must_exist=True)))
                       .add_option("filter_complex", filter_complex)
                       .map_stream("[v]")
                       .map_stream("0:a")
                       .set_video_codec("libx264")
                       .set_quality(crf=23, preset="veryfast")
                       .set_audio_codec("copy")
                       .add_option("shortest", "")
                       .set_output(str(validate_path(output_path)))
                       .build())

            run_ffmpeg(command, timeout=300)
            logger.info(f"Successfully processed video without background audio: {output_path}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except FFmpegError as e:
            # 其他异常（视频处理错误等）
            logger.error(f"[h2v] Failed to process video without background audio: {e}", exc_info=True)
            raise


def desc2image_gushi(
    basepath: str,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    loras=[],
    topic_extra={}
):
    """[LEGACY] 从描述生成图像，内部调用新模块"""
    data_path = os.path.join(basepath, "data.json")
    if not os.path.exists(data_path):
        return
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    srtdata = data["srtdata"]
    srtdata = saveimage(srtdata, basepath, width, height, loras, topic_extra)
    data["srtdata"] = srtdata
    with open(os.path.join(basepath, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return srtdata


def actor_generate(
    basepath: str, 
    content: str, 
    loras: List[Dict[str, Any]] = []
) -> None:
    """[LEGACY] 生成Actor图像，内部调用新模块"""
    return generate_actor_image(basepath, content, loras)


async def concat_videos_with_transitions(
    srtpath: str, 
    basepath: str = "", 
    possible_transitions: Optional[List[str]] = None
) -> Optional[str]:
    """[LEGACY] 合并视频（带过渡效果），内部调用新模块
    
    Args:
        srtpath: 字幕文件路径
        basepath: 基础路径
        possible_transitions: 可能的转场类型列表
        
    Returns:
        Optional[str]: 合并后的视频路径，失败返回None
    """
    if possible_transitions is None:
        possible_transitions = ["fade"]
    # 使用导入的函数，避免递归
    from utils.video_combiner import concat_videos_with_transitions as _concat_with_transitions
    return await _concat_with_transitions(srtpath, basepath, possible_transitions)


async def concat_videos(srtpath: str, basepath: str = "") -> Optional[str]:
    """[LEGACY] 合并视频，内部调用新模块
    
    Args:
        srtpath: 字幕文件路径
        basepath: 基础路径
        
    Returns:
        Optional[str]: 合并后的视频路径，失败返回None
    """
    from utils.video_combiner import concat_videos as _concat_videos
    return await _concat_videos(srtpath, basepath)


# 以下函数已迁移到新模块，不再保留旧实现：
# - run_ffmpeg_command: 已迁移到 utils.video_generator_steps
# - managed: 已迁移到 utils.video_generator_steps  
# - is_video_corrupted_opencv: 已迁移到 utils.video_processor
# - generate_video: 已迁移到 utils.video_generator_steps


async def videocombine(
    srtpath: str,
    audiopath: str,
    combined_video: str,
    subtitled_video: str,
    is_horizontal: bool,
    background_hex_color: str = "#578B2E",
    account_name: str = "",
) -> None:
    """[LEGACY] 为视频添加字幕和音频，内部调用新模块
    
    Args:
        srtpath: 字幕文件路径
        audiopath: 音频文件路径
        combined_video: 合并后的视频路径
        subtitled_video: 带字幕的视频路径
        is_horizontal: 是否横向
        background_hex_color: 背景颜色
        account_name: 账户名称
    """
    await add_subtitle_to_video(
        srtpath, audiopath, combined_video, subtitled_video,
        is_horizontal, background_hex_color, account_name
    )


async def videocombinewithlogo(
    subtitled_video: str, 
    logoed_video: str, 
    logopath: Optional[str]
) -> None:
    """[LEGACY] 为视频添加Logo，内部调用新模块
    
    Args:
        subtitled_video: 带字幕的视频路径
        logoed_video: 带Logo的视频路径
        logopath: Logo文件路径
    """
    if logopath:
        await add_logo_to_video(subtitled_video, logoed_video, logopath)


async def videocombineallwithlogo(
    srtpath,
    audiopath,
    combined_video,
    subtitled_video_output,
    logopath,
    is_horizontal,
    background_hex_color="#578B2E",
    account_name="",
):
    """[LEGACY] 为视频添加字幕和Logo，内部调用新模块"""
    await add_subtitle_and_logo_to_video(
        srtpath, audiopath, combined_video, subtitled_video_output,
        logopath, is_horizontal, background_hex_color, account_name
    )


# 主函数已移除，相关功能已迁移到新模块
