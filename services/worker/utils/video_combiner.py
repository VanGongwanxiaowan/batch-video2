"""视频合并模块

代码重构说明：
- 使用 core.utils.ffmpeg.builder 中的 FFmpegCommandBuilder
- 使用 build_concat_command 便捷函数简化合并操作
"""
import json
import os
import random
from typing import List, Optional

import pysrt
from utils.video_utils import hex_to_ffmpeg_abgr
from worker.config import settings

from core.logging_config import setup_logging
from core.utils.ffmpeg import FFmpegError, run_ffmpeg, run_ffmpeg_async, FFmpegCore
# 使用 FFmpeg 命令构建器
from core.utils.ffmpeg.builder import FFmpegCommandBuilder, build_concat_command

logger = setup_logging("worker.utils.video_combiner")

HUMAN_CONFIG_PATH = settings.human_config_path


async def concat_videos(srtpath: str, basepath: str = "") -> str:
    """
    使用FFmpeg concat方式合并视频 (异步)

    Args:
        srtpath: SRT文件路径
        basepath: 视频片段所在的基础路径

    Returns:
        合并后的视频文件路径

    代码重构说明：
        使用 FFmpegCommandBuilder 构建命令
    """
    video_paths = []
    srts = pysrt.open(srtpath, encoding="utf-8")
    for index, srt in enumerate(srts):
        videopath = os.path.join(basepath, f"{index}.mp4")
        if os.path.exists(videopath):
            video_paths.append(videopath)

    if not video_paths:
        logger.error("没有找到视频文件")
        raise ValueError("No video files found")

    combined_video_path = srtpath.replace("data.srt", "combined.mp4")

    # 使用构建器构建命令
    command = build_concat_command(video_paths, combined_video_path, method="concat")

    # 注入硬件加速参数 (如果在构建器中未处理，可以手动插入)
    # hw_args = FFmpegCore().get_hwaccel_args()
    # if hw_args:
    #    command = command[:1] + hw_args + command[1:]

    try:
        await run_ffmpeg_async(command, timeout=300)
        logger.info(f"视频合并成功: {combined_video_path}")
    except FFmpegError as e:
        logger.error(f"视频合并失败: {e}")
        raise

    return combined_video_path


async def concat_videos_with_transitions(
    srtpath: str,
    basepath: str = "",
    possible_transitions: List[str] = None,
) -> Optional[str]:
    """
    使用FFmpeg xfade滤镜拼接视频片段，并在每两段视频之间添加随机过渡效果 (异步)

    Args:
        srtpath: SRT文件路径
        basepath: 视频片段所在的基础路径
        possible_transitions: 可用的过渡效果列表

    Returns:
        合并后的视频文件路径，失败返回None

    代码重构说明：
        使用 FFmpegCommandBuilder 构建命令
    """
    if possible_transitions is None:
        possible_transitions = ["fade"]

    video_paths = []
    srts = pysrt.open(srtpath, encoding="utf-8")
    combined_video_path = srtpath.replace("data.srt", "combined.mp4")

    # 从data.json加载视频时长数据
    data_json_path = os.path.join(basepath, "data.json")
    try:
        with open(data_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            srtdata = data.get("srtdata", {})
    except FileNotFoundError:
        logger.error(f"未找到数据文件: {data_json_path}")
        return None
    except json.JSONDecodeError:
        logger.error(f"无法解析JSON文件: {data_json_path}")
        return None

    # 收集视频路径和时长
    start = 0
    durations = []
    for index in srtdata.keys():
        videopath = os.path.join(basepath, f"{index}.mp4")
        end = srtdata.get(index, {}).get("end", 0)
        duration = end - start
        start = end
        if os.path.exists(videopath):
            video_paths.append(videopath)
            durations.append(duration)
        else:
            logger.warning(f"视频文件不存在: {videopath}")

    num_videos = len(video_paths)
    if num_videos == 0:
        logger.error("没有找到视频文件")
        return None

    if num_videos == 1:
        # 如果只有一个视频，直接复制
        logger.info("仅找到一个视频，不应用过渡效果")
        try:
            command = (FFmpegCommandBuilder()
                       .add_input(str(video_paths[0]))
                       .add_option("c", "copy")
                       .set_output(str(combined_video_path))
                       .build())
            await run_ffmpeg_async(command, timeout=300)
            logger.info(f"视频复制成功: {combined_video_path}")
        except FFmpegError as e:
            logger.error(f"视频复制失败: {e}")
            raise
        return combined_video_path

    # 使用构建器构建xfade滤镜链
    transition_duration = 1.0  # 过渡持续时间（秒）
    cumulative_duration = 0.0

    builder = FFmpegCommandBuilder()

    # 添加所有输入
    for i, path in enumerate(video_paths):
        builder.add_input(str(path), index=i)

    # 构建xfade滤镜链
    for i in range(num_videos - 1):
        current_duration_ms = durations[i] if i < len(durations) else 0
        if current_duration_ms == 0:
            logger.warning(f"视频 {i}.mp4 的时长未找到或为0，使用默认时长5.0秒")
            current_duration_seconds = 5.0
        else:
            current_duration_seconds = current_duration_ms / 1000.0

        selected_transition = random.choice(possible_transitions)

        if i == num_videos - 2:
            output_stream = "out"
        else:
            output_stream = f"vtemp{i}"

        xfade_offset = cumulative_duration + current_duration_seconds
        if xfade_offset < 0:
            xfade_offset = 0

        # 添加 xfade 滤镜
        if i == 0:
            input1 = f"[0:v]"
        else:
            input1 = f"[vtemp{i-1}]"

        builder.add_xfade_filter(
            transition=selected_transition,
            duration=transition_duration,
            offset=xfade_offset,
            input1=input1,
            input2=f"[{i+1}:v]",
            output=output_stream
        )

        cumulative_duration += current_duration_seconds

    # 映射输出并设置参数
    builder.map_stream("[out]")
    builder.add_option("vsync", "2")
    builder.add_option("preset", "veryfast")
    
    # 尝试应用硬件加速
    hw_args = FFmpegCore().get_hwaccel_args()
    if hw_args:
         # 注意：xfade 是 CPU 滤镜，硬件加速可能需要复杂的 hwupload/hwdownload
         # 这里简单添加 hwaccel 参数，如果失败可能需要回退
         # 为了安全起见，xfade 复杂滤镜暂不强制使用 hwaccel 除非经过验证
         pass

    builder.set_output(str(combined_video_path))

    command = builder.build()

    try:
        logger.info(f"执行FFmpeg命令（带过渡效果）: {' '.join(command)}")
        await run_ffmpeg_async(command, timeout=600)
        logger.info(f"视频合并成功（带过渡效果）: {combined_video_path}")
    except FFmpegError as e:
        logger.error(f"视频合并失败（带过渡效果）: {e}")
        raise

    return combined_video_path

