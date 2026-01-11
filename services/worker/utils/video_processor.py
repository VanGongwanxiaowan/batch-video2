"""视频处理模块"""
import json
import os
import random
from typing import Any, Dict, List, Optional

import cv2
import pysrt
from worker.config import settings

from core.logging_config import setup_logging
from core.utils.ffmpeg import (
    FFmpegError,
    ffmpeg_utils,
    run_ffmpeg,
    validate_path,
)

logger = setup_logging("worker.utils.video_processor")

BG_AUDIO_DIR = settings.bg_audio_dir
FONT_DIR = settings.font_dir


def compare_video(duration: float, output_image_path: str, output_path: str) -> None:
    """
    从合适的时长超过 duration 的视频中随机抽取一个，然后ffmpeg裁剪时长 duration 输出到 output_path
    截取首帧到 output_image_path
    
    Args:
        duration: 视频时长（秒）
        output_image_path: 输出图像路径
        output_path: 输出视频路径
    """
    duration_map_path = "duration_map.json"
    if not os.path.exists(duration_map_path):
        logger.error(f"duration_map.json 不存在: {duration_map_path}")
        raise FileNotFoundError(f"duration_map.json not found: {duration_map_path}")
    
    with open(duration_map_path, "r", encoding="utf-8") as f:
        duration_map = json.load(f)

    video_list = []
    for k, v in duration_map.items():
        if int(k) > duration:
            video_list.extend(v)
    
    if not video_list:
        logger.error(f"没有找到时长超过 {duration} 秒的视频")
        raise ValueError(f"No videos found with duration > {duration}")
    
    video = random.choice(video_list)
    
    try:
        ffmpeg_utils.cut_video(video, output_path, start_time=0, duration=duration)
        # 提取首帧
        ffmpeg_utils.extract_frame(video, output_image_path, frame_number=0)
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, PermissionError, FileNotFoundError) as e:
        # 文件系统错误
        logger.error(f"[compare_video] 文件系统错误: {e}", exc_info=True)
        raise
    except FFmpegError as e:
        # FFmpeg处理错误
        logger.error(f"[compare_video] FFmpeg处理失败: {e}", exc_info=True)
        raise
    except Exception as e:
        # 其他异常
        logger.error(f"[compare_video] 视频处理失败: {e}", exc_info=True)
        raise


def is_video_corrupted(file_path: str) -> bool:
    """
    检查视频是否损坏
    
    Args:
        file_path: 视频文件路径
        
    Returns:
        如果视频损坏返回True
    """
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        try:
            os.unlink(file_path)
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError) as e:
            # 文件系统错误，记录但不抛出
            logger.warning(f"[is_video_corrupted] 删除损坏视频失败: {file_path}, error={e}")
        except Exception as e:
            # 其他异常
            logger.warning(f"[is_video_corrupted] 删除损坏视频时发生未知异常: {file_path}, error={e}")
        return True
    cap.release()
    return False

