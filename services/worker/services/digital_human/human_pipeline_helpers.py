"""数字人合成辅助函数模块

提取公共逻辑，减少重复代码。

注意：此模块已重构，部分功能已迁移到独立模块：
- PathManager -> path_manager.HumanPathManager
- 音频处理 -> audio_processor
- 视频处理 -> video_processor

为了保持向后兼容，此文件保留原有接口，但内部调用新模块。
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.logging_config import setup_logging

from .audio_processor import extract_audio_segment as _extract_audio_segment

# 导入新模块
from .path_manager import HumanPathManager
from .video_processor import (
    TRANSITION_DURATION,
)
from .video_processor import apply_xfade_transition as _apply_xfade_transition
from .video_processor import concat_videos_ffmpeg as _concat_videos_ffmpeg
from .video_processor import concat_videos_with_xfade as _concat_videos_with_xfade
from .video_processor import extract_video_segment as _extract_video_segment
from .video_processor import normalize_human_video as _normalize_human_video
from .video_processor import overlay_corner_human as _overlay_corner_human

logger = setup_logging("worker.digital_human.helpers")


@dataclass
class HumanConfig:
    """数字人配置"""
    path: str
    duration: float = 18.0
    end_duration: float = 0.0


# 向后兼容：保留 PathManager 别名
PathManager = HumanPathManager


def load_human_config(account_name: str, account_extra: Dict[str, Any]) -> HumanConfig:
    """加载数字人配置。
    
    Args:
        account_name: 账户名称，用于构建默认视频路径
        account_extra: 账户额外配置字典，可能包含human_config键
        
    Returns:
        HumanConfig: 数字人配置对象
        
    Note:
        - 如果account_extra中没有human_config，使用默认配置
        - 默认视频路径为: {human_assets_path}/{account_name}.mp4
        - 默认duration为18秒，end_duration为0秒
    """
    from config import settings
    
    base_path = str(settings.human_assets_path)
    video_path = os.path.join(base_path, f"{account_name}.mp4")
    
    config = account_extra.get(
        "human_config",
        {
            "path": video_path,
            "duration": 120,
            "end_duration": 0,
        },
    )
    
    return HumanConfig(
        path=config.get("path", video_path),
        duration=config.get("duration", 18),
        end_duration=config.get("end_duration", 0),
    )


def load_srt_data(jsonpath: str) -> List[Dict[str, Any]]:
    """加载字幕数据。
    
    Args:
        jsonpath: JSON文件路径
        
    Returns:
        List[Dict[str, Any]]: 字幕数据列表，每个元素包含start、end、text等字段
        
    Raises:
        FileNotFoundError: 如果文件不存在
        json.JSONDecodeError: 如果JSON格式无效
        KeyError: 如果JSON中缺少srtdata键
    """
    try:
        with open(jsonpath, "r", encoding="utf-8") as f:
            jsondata = json.load(f)
        
        if "srtdata" not in jsondata:
            raise KeyError(f"JSON文件缺少'srtdata'键: {jsonpath}")
        
        srtdata = jsondata["srtdata"]
        return list(srtdata.values())
    except FileNotFoundError:
        logger.error(f"字幕文件不存在: {jsonpath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON文件格式无效: {jsonpath}, error: {e}")
        raise
    except KeyError:
        raise
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（字幕数据加载错误等）
        logger.error(f"[load_subtitle_data] 加载字幕数据失败: {jsonpath}, error: {e}", exc_info=True)
        raise


def calculate_durations(
    srts: List[Dict[str, Any]],
    config: HumanConfig
) -> Tuple[float, float]:
    """计算前段和结尾时长。
    
    Args:
        srts: 字幕数据列表，每个元素包含start和end字段（毫秒）
        config: 数字人配置对象
        
    Returns:
        Tuple[float, float]: (前段时长, 结尾时长)，单位为秒
        
    Note:
        - 前段时长：从开始到config.duration的最大时长
        - 结尾时长：如果config.end_duration > 0，计算结尾部分的时长
        - 字幕时间戳需要除以1000转换为秒
    """
    if not srts:
        return 0.0, 0.0
    
    duration = 0.0
    for srt in srts:
        end = srt["end"] / 1000
        if end > duration:
            duration = end
        if duration > config.duration:
            break
    
    end = srts[-1]["end"] / 1000
    end_duration = 0.0
    if config.end_duration > 0:
        for srt in reversed(srts):
            start = srt["start"] / 1000
            if end_duration < config.end_duration:
                end_duration = end - start
            else:
                break
    
    return duration, end_duration


# 向后兼容：导出音频处理函数
def extract_audio_segment(
    audio_path: str,
    output_path: str,
    start_time: float = 0.0,
    duration: Optional[float] = None,
) -> None:
    """提取音频片段（向后兼容，内部调用新模块）"""
    _extract_audio_segment(audio_path, output_path, start_time, duration)


# 向后兼容：导出视频处理函数
def extract_video_segment(
    video_path: str,
    output_path: str,
    start_time: float = 0.0,
    end_time: Optional[float] = None,
    duration: Optional[float] = None,
) -> None:
    """提取视频片段（向后兼容，内部调用新模块）"""
    _extract_video_segment(video_path, output_path, start_time, end_time, duration)


def post_human_generate(audio_path: str, video_path: str, save_path: str) -> None:
    """调用数字人服务生成视频。
    
    支持本地推理引擎 (HeyGem) 和远程 API 调用。
    
    Args:
        audio_path: 音频文件路径
        video_path: 视频文件路径
        save_path: 保存路径
        
    Raises:
        requests.RequestException: 如果HTTP请求失败
        ValueError: 如果路径无效
        Exception: 本地推理失败
    """
    import os
    from config import settings

    # 验证文件路径
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    # 优先尝试本地生成 (如果配置启用)
    use_local = os.getenv("USE_LOCAL_HUMAN_GENERATION", "false").lower() == "true"
    
    if use_local:
        try:
            logger.info("尝试使用本地 HeyGem 推理引擎生成数字人...")
            from .heygem import HeyGemInferenceEngine
            engine = HeyGemInferenceEngine()
            engine.generate(video_path, audio_path, save_path)
            logger.info(f"本地生成成功: {save_path}")
            return
        except ImportError:
            logger.warning("HeyGem 模块未找到或依赖缺失，回退到远程 API")
        except Exception as e:
            logger.error(f"本地生成失败: {e}，回退到远程 API", exc_info=True)
            # Fallback to remote

    request_data = {
        "audio_path": str(audio_path),
        "video_path": str(video_path),
        "save_path": str(save_path),
    }
    
    url = f"{settings.HUMAN_SERVICE_URL}/human/generate"
    logger.info(f"调用数字人服务生成视频: url={url}, audio_path={audio_path}, video_path={video_path}")
    
    try:
        response = requests.post(
            url,
            json=request_data,
            timeout=300
        )
        response.raise_for_status()  # 如果状态码不是2xx，抛出异常
        logger.info(f"数字人服务调用成功: save_path={save_path}")
    except requests.Timeout:
        logger.error(f"数字人服务调用超时: url={url}, timeout=300s")
        raise
    except requests.RequestException as e:
        logger.error(
            f"数字人服务调用失败: url={url}, error={e}",
            exc_info=True
        )
        raise


# 向后兼容：导出视频处理函数
def normalize_human_video(
    input_path: str,
    output_path: str,
    width: int = 1360,
    height: int = 768,
) -> None:
    """标准化数字人视频（向后兼容，内部调用新模块）"""
    _normalize_human_video(input_path, output_path, width, height)


def concat_videos_ffmpeg(video_paths: List[str], output_path: str) -> None:
    """使用 ffmpeg concat 方式拼接视频列表（向后兼容，内部调用新模块）"""
    _concat_videos_ffmpeg(video_paths, output_path)


def apply_xfade_transition(
    video1_path: str,
    video2_path: str,
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = TRANSITION_DURATION,
) -> None:
    """应用 xfade 转场效果（向后兼容，内部调用新模块）"""
    _apply_xfade_transition(video1_path, video2_path, output_path, transition_type, transition_duration)


def overlay_corner_human(
    main_video_path: str,
    human_video_path: str,
    output_path: str,
    position: Tuple[int, int] = (1000, 300),
) -> None:
    """在主视频上叠加角标数字人（向后兼容，内部调用新模块）"""
    _overlay_corner_human(main_video_path, human_video_path, output_path, position)


def concat_videos_with_xfade(
    video_paths: List[str],
    output_path: str,
    transition_type: str = "fade",
    transition_duration: float = TRANSITION_DURATION,
) -> None:
    """使用 xfade 依次拼接多个视频（向后兼容，内部调用新模块）"""
    _concat_videos_with_xfade(video_paths, output_path, transition_type, transition_duration)

