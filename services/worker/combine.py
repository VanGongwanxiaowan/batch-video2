import json
import os
import random
import re
import sys
from pathlib import Path
from subprocess import TimeoutExpired
from typing import Optional

import pysrt

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging
from core.utils.ffmpeg import (
    FFmpegError,
)
from core.utils.ffmpeg import get_video_duration as safe_get_video_duration
from core.utils.ffmpeg import (
    run_ffmpeg,
    validate_path,
)

# 配置日志
logger = setup_logging("worker.combine", log_to_file=False)

def get_video_duration(video_path: str) -> float:
    """获取视频精确时长（秒）"""
    return safe_get_video_duration(video_path)

def concat_videos_with_transitions(
    srtpath: str, 
    basepath: str = ""
) -> Optional[str]:
    """
    合并视频（带转场效果）
    
    Args:
        srtpath: 字幕文件路径
        basepath: 视频片段所在的基础路径
        
    Returns:
        合并后的视频文件路径，失败返回None
    """
    # 收集所有视频路径
    video_paths = []
    index = 0
    while True:
        videopath = os.path.join(basepath, f"{index}.mp4")
        if os.path.exists(videopath):
            video_paths.append(videopath)
            index += 1
        else:
            break

    if not video_paths:
        logger.warning("未找到视频文件以进行拼接。")
        return None

    logger.info(f"视频片段总数: {len(video_paths)}")

    # 获取精确视频时长
    durations = [get_video_duration(path) for path in video_paths]
    total_duration = sum(durations)
    logger.info(f"原始总时长: {total_duration/60:.2f}分钟")

    # 过渡参数设置
    transition_duration = 1.0
    possible_transitions = ["fade", "fadeblack", "wipeleft", "circleopen"]
    num_transitions = len(video_paths) - 1

    # 单视频处理
    if len(video_paths) == 1:
        logger.info("仅找到一个视频。不应用过渡效果。")
        combined_video_path = os.path.join(basepath, "combined_output.mp4")
        input_video = str(validate_path(video_paths[0], must_exist=True))
        combined_video_path = str(validate_path(combined_video_path))
        run_ffmpeg([
            '-y', '-i', input_video,
            '-c:v', 'libx264', '-preset', 'slow', '-crf', '22',
            '-an', combined_video_path
        ])
        return combined_video_path

    # 构建FFmpeg滤镜链
    filter_complex = []
    input_args = []
    for path in video_paths:
        input_args.extend(['-i', str(validate_path(path, must_exist=True))])
    
    # 添加输入流标签
    for i in range(len(video_paths)):
        filter_complex.append(f"[{i}:v]setpts=PTS-STARTPTS[v{i}];")
    
    # 添加过渡效果
    for i in range(num_transitions):
        transition = random.choice(possible_transitions)
        offset = max(0.0, sum(durations[:i+1]) - transition_duration)  # 关键修正：确保偏移量非负
        
        # 第一个过渡特殊处理
        if i == 0:
            prev = f"[v0]"
        else:
            prev = f"[t{i-1}]"
        
        filter_complex.append(
            f"{prev}[v{i+1}]xfade=transition={transition}:"
            f"duration={transition_duration}:offset={offset:.3f}[t{i}];"
        )
    
    # 最终输出
    filter_complex.append(f"[t{num_transitions-1}]format=yuv420p[vout]")
    filter_str = "\n".join(filter_complex)

    # 输出文件路径
    combined_video_path = str(validate_path(os.path.join(basepath, "combined_output.mp4")))
    
    # 构建FFmpeg命令
    ffmpeg_args = [
        '-y',
        *input_args,
        '-filter_complex',
        filter_str,
        '-map',
        '[vout]',
        '-c:v',
        'libx264',
        '-preset',
        'veryfast',
        '-crf',
        '22',
        '-movflags',
        '+faststart',
        '-an',
        '-x264-params',
        'keyint=30:min-keyint=30:scenecut=0',
        combined_video_path,
    ]

    # 记录执行信息
    logger.info(f"执行FFmpeg命令（简化显示）...")
    logger.info(f"实际过渡次数: {num_transitions}, 总输出时长: {total_duration - num_transitions*transition_duration:.2f}秒")
    
    try:
        run_ffmpeg(ffmpeg_args, capture_output=False)
        
        # 验证输出
        output_duration = get_video_duration(combined_video_path)
        expected_duration = total_duration - num_transitions*transition_duration
        logger.info(f"输出视频实际时长: {output_duration:.2f}秒, 预期: {expected_duration:.2f}秒")
        
        return combined_video_path
    except (FFmpegError, TimeoutExpired) as e:
        logger.exception(f"FFmpeg命令执行失败: {e}")
        return None


# 使用示例保持不变
if __name__ == "__main__":
    example_base = "./sample_jobs/job_1"
    srtpath = os.path.join(example_base, "data.srt")
    combined_video = concat_videos_with_transitions(srtpath, example_base)
    if combined_video:
        logger.info(f"视频拼接完成，输出文件：{combined_video}")
