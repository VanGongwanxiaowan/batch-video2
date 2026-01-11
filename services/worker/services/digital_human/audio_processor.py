"""数字人音频处理模块

负责音频提取、裁剪等操作。
"""

from typing import Optional

from core.logging_config import setup_logging
from core.utils.ffmpeg import run_ffmpeg, validate_path

logger = setup_logging("worker.digital_human.audio")


def extract_audio_segment(
    audio_path: str,
    output_path: str,
    start_time: float = 0.0,
    duration: Optional[float] = None,
) -> None:
    """
    提取音频片段
    
    Args:
        audio_path: 输入音频路径
        output_path: 输出音频路径
        start_time: 开始时间（秒）
        duration: 时长（秒），如果为None则提取到结尾
    """
    audio_valid = validate_path(audio_path, must_exist=True)
    output_valid = validate_path(output_path)
    
    cmd = ["-y", "-i", str(audio_valid)]
    if start_time > 0:
        cmd.extend(["-ss", str(start_time)])
    if duration:
        cmd.extend(["-t", str(duration)])
    cmd.extend(["-acodec", "copy", str(output_valid)])
    
    run_ffmpeg(cmd)
    logger.debug(f"音频片段提取完成: {output_path}")

