"""数字人视频处理模块

负责视频提取、标准化、合并、转场等操作。
"""

import shutil
import tempfile
from typing import List, Optional, Tuple

from core.logging_config import setup_logging
from core.utils.ffmpeg import get_video_duration as safe_get_video_duration
from core.utils.ffmpeg import (
    run_ffmpeg,
    validate_path,
)

logger = setup_logging("worker.digital_human.video")

TRANSITION_DURATION = 0.5  # seconds


def extract_video_segment(
    video_path: str,
    output_path: str,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
    duration: Optional[float] = None,
) -> None:
    """
    提取视频片段
    
    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        start_time: 开始时间（秒）
        end_time: 结束时间（秒）
        duration: 时长（秒），如果指定了end_time则忽略此参数
    """
    video_valid = validate_path(video_path, must_exist=True)
    output_valid = validate_path(output_path)
    
    cmd = ["-y", "-i", str(video_valid)]
    if start_time > 0:
        cmd.extend(["-ss", str(start_time)])
    if end_time:
        cmd.extend(["-to", str(end_time)])
    elif duration:
        cmd.extend(["-t", str(duration)])
    cmd.extend(["-c", "copy", str(output_valid)])
    
    run_ffmpeg(cmd)
    logger.debug(f"视频片段提取完成: {output_path}")


def normalize_human_video(
    input_path: str,
    output_path: str,
    width: int = 1360,
    height: int = 768,
) -> None:
    """
    标准化数字人视频（调整分辨率、帧率等）
    
    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        width: 目标宽度
        height: 目标高度
    """
    input_valid = validate_path(input_path, must_exist=True)
    output_valid = validate_path(output_path)
    
    run_ffmpeg([
        "-y",
        "-i", str(input_valid),
        "-an",
        "-r", "30",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={width}:{height}:flags=lanczos,setsar=1",
        str(output_valid),
    ])
    logger.debug(f"视频标准化完成: {output_path}")


def concat_videos_ffmpeg(video_paths: List[str], output_path: str) -> None:
    """
    使用 ffmpeg concat 方式拼接视频列表
    
    Args:
        video_paths: 视频路径列表
        output_path: 输出视频路径
    """
    with tempfile.NamedTemporaryFile(mode="w+", delete=True, suffix=".txt") as temp_file:
        for v in video_paths:
            temp_file.write(f"file '{v}'\n")
        temp_file.flush()
        list_path = temp_file.name
        
        validated_output = validate_path(output_path)
        run_ffmpeg([
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            str(validated_output)
        ])
    logger.debug(f"视频拼接完成: {output_path}")


def apply_xfade_transition(
    video1_path: str,
    video2_path: str,
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = TRANSITION_DURATION,
) -> None:
    """
    应用 xfade 转场效果
    
    Args:
        video1_path: 第一个视频路径
        video2_path: 第二个视频路径
        output_path: 输出视频路径
        transition_type: 转场类型（如 "fade", "wipeleft" 等）
        transition_duration: 转场时长（秒）
    """
    video1_valid = validate_path(video1_path, must_exist=True)
    video2_valid = validate_path(video2_path, must_exist=True)
    output_valid = validate_path(output_path)
    
    video1_duration = safe_get_video_duration(str(video1_valid))
    offset = max(0, video1_duration - transition_duration)
    
    run_ffmpeg([
        "-y",
        "-i", str(video1_valid),
        "-i", str(video2_valid),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset}[v]",
        "-map", "[v]",
        "-an",
        str(output_valid),
    ])
    logger.debug(f"转场效果应用完成: {output_path}")


def overlay_corner_human(
    main_video_path: str,
    human_video_path: str,
    output_path: str,
    position: Tuple[int, int] = (1000, 300),
) -> None:
    """
    在主视频上叠加角标数字人（绿幕抠图）
    
    Args:
        main_video_path: 主视频路径
        human_video_path: 数字人视频路径
        output_path: 输出视频路径
        position: 叠加位置 (x, y)
    """
    main_valid = validate_path(main_video_path, must_exist=True)
    human_valid = validate_path(human_video_path, must_exist=True)
    output_valid = validate_path(output_path)
    
    x, y = position
    filter_complex = (
        f"[1:v]colorkey=0x00ff00:0.3:0.2,scale=300:-1[fg];"
        f"[0:v][fg]overlay={x}:{y}::eof_action=pass"
    )
    
    run_ffmpeg([
        "-y",
        "-i", str(main_valid),
        "-i", str(human_valid),
        "-filter_complex", filter_complex,
        str(output_valid),
    ])
    logger.debug(f"角标数字人叠加完成: {output_path}")


def concat_videos_with_xfade(
    video_paths: List[str],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = TRANSITION_DURATION,
) -> None:
    """
    使用 xfade 依次拼接多个视频
    
    Args:
        video_paths: 视频路径列表
        output_path: 输出视频路径
        transition_type: 转场类型
        transition_duration: 转场时长（秒）
    """
    if not video_paths:
        return
    
    if len(video_paths) == 1:
        shutil.copyfile(video_paths[0], output_path)
        return
    
    current = validate_path(video_paths[0], must_exist=True)
    for next_video in video_paths[1:]:
        next_valid = validate_path(next_video, must_exist=True)
        temp_out = output_path.replace(".mp4", "_xfade_temp.mp4")
        temp_valid = validate_path(temp_out)
        
        apply_xfade_transition(
            str(current),
            str(next_valid),
            str(temp_valid),
            transition_type,
            transition_duration,
        )
        current = temp_valid
    
    shutil.copyfile(current, output_path)
    logger.debug(f"视频转场拼接完成: {output_path}")

