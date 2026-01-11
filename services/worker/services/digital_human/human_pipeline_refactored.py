"""数字人合成底层实现（重构版）

使用辅助函数模块，代码更简洁、易维护。
"""

import random
import shutil
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.logging_config import setup_logging
from core.utils.ffmpeg import get_video_duration as safe_get_video_duration

from .human_pipeline_helpers import (
    TRANSITION_DURATION,
    HumanConfig,
    PathManager,
    apply_xfade_transition,
    calculate_durations,
    concat_videos_ffmpeg,
    concat_videos_with_xfade,
    extract_audio_segment,
    extract_video_segment,
    load_human_config,
    load_srt_data,
    normalize_human_video,
    overlay_corner_human,
    post_human_generate,
)

logger = setup_logging("worker.digital_human.pipeline")


@dataclass
class CornerConfig:
    """角标模式配置数据类
    
    Attributes:
        intro_duration: 开头数字人时长（秒）
        outro_duration: 结尾数字人时长（秒）
        human_video_source_path: 数字人视频源路径
    """
    intro_duration: float
    outro_duration: float
    human_video_source_path: str


def _load_corner_config(
    account_extra: Dict[str, Any],
    default_config: HumanConfig,
) -> CornerConfig:
    """加载角标模式配置
    
    Args:
        account_extra: 账户额外配置
        default_config: 默认数字人配置
        
    Returns:
        CornerConfig: 角标配置对象
    """
    corner_config = account_extra.get(
        "human_config",
        {
            "path": default_config.path,
            "duration": 10,
            "end_duration": 10,
        },
    )
    return CornerConfig(
        intro_duration=corner_config.get("duration", 10),
        outro_duration=corner_config.get("end_duration", 10),
        human_video_source_path=corner_config.get("path", default_config.path),
    )


def _calculate_corner_durations(
    total_video_duration: float,
    intro_duration_account: float,
    outro_duration_account: float,
) -> Tuple[float, float, float]:
    """计算角标模式的时长配置
    
    Args:
        total_video_duration: 主视频总时长
        intro_duration_account: 账户配置的开头时长
        outro_duration_account: 账户配置的结尾时长
        
    Returns:
        (intro_duration, outro_duration, middle_duration): 开头、结尾、中间段时长
    """
    intro_duration = min(intro_duration_account, total_video_duration)
    outro_duration = min(outro_duration_account, total_video_duration - intro_duration)
    middle_duration = max(0, total_video_duration - intro_duration - outro_duration)
    return intro_duration, outro_duration, middle_duration


def _generate_corner_human_segments(
    paths: PathManager,
    audio_path: str,
    corner_config: CornerConfig,
    intro_duration: float,
    outro_duration: float,
) -> None:
    """生成角标模式的数字人片段（开头和结尾）
    
    Args:
        paths: 路径管理器
        audio_path: 音频文件路径
        corner_config: 角标配置
        intro_duration: 开头时长
        outro_duration: 结尾时长
    """
    # 生成开头数字人
    if intro_duration > 0:
        extract_audio_segment(audio_path, paths.short_audio_intro, duration=intro_duration)
        post_human_generate(
            paths.short_audio_intro,
            corner_config.human_video_source_path,
            paths.human_generate_intro,
        )
        normalize_human_video(paths.human_generate_intro, paths.human_video_intro_final)
    
    # 生成结尾数字人
    if outro_duration > 0:
        audio_start_for_outro = safe_get_video_duration(audio_path) - outro_duration
        extract_audio_segment(
            audio_path,
            paths.short_audio_outro,
            start_time=audio_start_for_outro,
            duration=outro_duration,
        )
        post_human_generate(
            paths.short_audio_outro,
            corner_config.human_video_source_path,
            paths.human_generate_outro,
        )
        normalize_human_video(paths.human_generate_outro, paths.human_video_outro_final)


def _split_main_video_for_corner(
    paths: PathManager,
    origin_video_path: str,
    intro_duration: float,
    outro_duration: float,
    middle_duration: float,
    total_duration: float,
) -> None:
    """切分主视频为开头、中间、结尾三段
    
    Args:
        paths: 路径管理器
        origin_video_path: 原始视频路径
        intro_duration: 开头时长
        outro_duration: 结尾时长
        middle_duration: 中间段时长
        total_duration: 视频总时长
    """
    # 切分开头段
    if intro_duration > 0:
        extract_video_segment(origin_video_path, paths.main_video_part1, duration=intro_duration)
    
    # 切分结尾段
    if outro_duration > 0:
        outro_start_time = total_duration - outro_duration
        extract_video_segment(
            origin_video_path,
            paths.main_video_part3,
            start_time=outro_start_time,
        )
    
    # 切分中间段
    if middle_duration > 0:
        middle_start_time = intro_duration
        extract_video_segment(
            origin_video_path,
            paths.main_video_part2,
            start_time=middle_start_time,
            duration=middle_duration,
        )


def _overlay_corner_humans(
    paths: PathManager,
    intro_duration: float,
    outro_duration: float,
) -> None:
    """叠加角标数字人到主视频片段
    
    Args:
        paths: 路径管理器
        intro_duration: 开头时长
        outro_duration: 结尾时长
    """
    # 叠加开头角标
    if intro_duration > 0:
        overlay_corner_human(
            paths.main_video_part1,
            paths.human_video_intro_final,
            paths.part1_with_human,
        )
    else:
        paths.part1_with_human = paths.main_video_part1
    
    # 叠加结尾角标
    if outro_duration > 0:
        overlay_corner_human(
            paths.main_video_part3,
            paths.human_video_outro_final,
            paths.part3_with_human,
        )
    else:
        paths.part3_with_human = paths.main_video_part3


def _build_corner_video_list(
    paths: PathManager,
    intro_duration: float,
    middle_duration: float,
    outro_duration: float,
) -> List[str]:
    """构建角标模式的视频片段列表
    
    Args:
        paths: 路径管理器
        intro_duration: 开头时长
        middle_duration: 中间段时长
        outro_duration: 结尾时长
        
    Returns:
        视频片段路径列表
    """
    video_list = []
    if intro_duration > 0:
        video_list.append(paths.part1_with_human)
    if middle_duration > 0:
        video_list.append(paths.main_video_part2)
    if outro_duration > 0:
        video_list.append(paths.part3_with_human)
    return video_list


def _concat_corner_videos(
    video_list: List[str],
    output_path: str,
    use_transition: bool = False,
    transition_type: Optional[str] = None,
) -> None:
    """拼接角标模式的视频片段
    
    Args:
        video_list: 视频片段路径列表
        output_path: 输出路径
        use_transition: 是否使用转场效果
        transition_type: 转场类型（仅在use_transition=True时有效）
    """
    if not video_list:
        # 如果没有片段，应该不会发生，但为了安全起见
        return
    
    if len(video_list) == 1:
        shutil.copyfile(video_list[0], output_path)
    elif use_transition and transition_type:
        concat_videos_with_xfade(video_list, output_path, transition_type)
    else:
        concat_videos_ffmpeg(video_list, output_path)


def human_pack_new(
    account_name: str,
    origin_video_path: str,
    audio_path: str,
    jsonpath: str,
    account_extra: Dict[str, Any],
) -> str:
    """全屏数字人主流程（无转场或通过裁剪实现衔接）。"""
    paths = PathManager(origin_video_path)
    config = load_human_config(account_name, account_extra)
    srts = load_srt_data(jsonpath)
    
    duration, end_duration = calculate_durations(srts, config)
    
    # 截取前段音频
    extract_audio_segment(audio_path, paths.short_audio, duration=duration)
    
    # 截取原视频后段
    extract_video_segment(origin_video_path, paths.origin_cut_video, start_time=duration)
    
    # 生成前半段数字人
    post_human_generate(paths.short_audio, config.path, paths.output)
    normalize_human_video(paths.output, paths.human_video_final)
    
    if config.end_duration <= 0:
        # 直接拼接
        concat_videos_ffmpeg([paths.human_video_final, paths.origin_cut_video], paths.human_replaced_video)
        return paths.human_replaced_video
    
    # 需要结尾数字人段落
    concat_videos_ffmpeg([paths.human_video_final, paths.origin_cut_video], paths.temp_video)
    
    end = srts[-1]["end"] / 1000
    cut_start = end - end_duration
    
    # 截取结尾音频
    extract_audio_segment(audio_path, paths.short_audio_end, start_time=cut_start)
    
    # 截取原视频结尾前段
    extract_video_segment(paths.temp_video, paths.origin_cut_end_video, end_time=cut_start)
    
    # 生成结尾数字人
    post_human_generate(paths.short_audio_end, config.path, paths.human_generate_end)
    normalize_human_video(paths.human_generate_end, paths.human_video_end_final)
    
    # 拼接
    concat_videos_ffmpeg([paths.origin_cut_end_video, paths.human_video_end_final], paths.human_replaced_video)
    return paths.human_replaced_video


def human_pack_new_with_transition(
    account_name: str,
    origin_video_path: str,
    audio_path: str,
    jsonpath: str,
    account_extra: Dict[str, Any],
) -> str:
    """全屏数字人 + 过渡特效版本。"""
    paths = PathManager(origin_video_path)
    config = load_human_config(account_name, account_extra)
    srts = load_srt_data(jsonpath)
    
    duration, end_duration = calculate_durations(srts, config)
    
    # 转场配置
    transition_enabled = account_extra.get("enable_transition", False)
    transition_types = account_extra.get("transition_types", ["fade"])
    transition_type = random.choice(transition_types) if transition_types else "fade"
    
    adjusted_duration = max(0, duration - TRANSITION_DURATION) if transition_enabled else duration
    
    # 截取前段音频
    extract_audio_segment(audio_path, paths.short_audio, duration=adjusted_duration)
    
    # 截取原视频后段
    extract_video_segment(origin_video_path, paths.origin_cut_video, start_time=adjusted_duration)
    
    # 生成前半段数字人
    post_human_generate(paths.short_audio, config.path, paths.output)
    normalize_human_video(paths.output, paths.human_video_final)
    
    if config.end_duration <= 0:
        if transition_enabled:
            apply_xfade_transition(
                paths.human_video_final,
                paths.origin_cut_video,
                paths.human_replaced_video,
                transition_type,
            )
        else:
            concat_videos_ffmpeg([paths.human_video_final, paths.origin_cut_video], paths.human_replaced_video)
        return paths.human_replaced_video
    
    # 需要结尾段
    if transition_enabled:
        apply_xfade_transition(
            paths.human_video_final,
            paths.origin_cut_video,
            paths.temp_video,
            transition_type,
        )
    else:
        concat_videos_ffmpeg([paths.human_video_final, paths.origin_cut_video], paths.temp_video)
    
    end = srts[-1]["end"] / 1000
    cut_start = end - end_duration
    
    # 截取结尾音频
    extract_audio_segment(audio_path, paths.short_audio_end, start_time=cut_start)
    
    # 截取原视频结尾前段
    extract_video_segment(
        paths.temp_video,
        paths.origin_cut_end_video,
        end_time=cut_start + TRANSITION_DURATION,
    )
    
    # 生成结尾数字人
    post_human_generate(paths.short_audio_end, config.path, paths.human_generate_end)
    normalize_human_video(paths.human_generate_end, paths.human_video_end_final)
    
    if transition_enabled:
        apply_xfade_transition(
            paths.origin_cut_end_video,
            paths.human_video_end_final,
            paths.human_replaced_video,
            transition_type,
        )
    else:
        concat_videos_ffmpeg([paths.origin_cut_end_video, paths.human_video_end_final], paths.human_replaced_video)
    
    return paths.human_replaced_video


def human_pack_new_corner(
    account_name: str,
    origin_video_path: str,
    audio_path: str,
    jsonpath: str,
    account_extra: Dict[str, Any],
) -> str:
    """角标模式：在主视频开头/结尾叠加绿幕数字人。
    
    此函数已重构，提取了重复逻辑到辅助函数，提高了代码可维护性。
    
    Args:
        account_name: 账户名称
        origin_video_path: 原始视频路径
        audio_path: 音频文件路径
        jsonpath: JSON文件路径（未使用，保留用于向后兼容）
        account_extra: 账户额外配置
        
    Returns:
        str: 生成的视频路径
    """
    paths = PathManager(origin_video_path)
    config = load_human_config(account_name, account_extra)
    
    # 加载角标配置
    corner_config = _load_corner_config(account_extra, config)
    
    # 计算时长
    total_duration = safe_get_video_duration(origin_video_path)
    intro_duration, outro_duration, middle_duration = _calculate_corner_durations(
        total_duration,
        corner_config.intro_duration,
        corner_config.outro_duration,
    )
    
    # 生成数字人片段
    _generate_corner_human_segments(
        paths, audio_path, corner_config, intro_duration, outro_duration
    )
    
    # 切分主视频
    _split_main_video_for_corner(
        paths, origin_video_path, intro_duration, outro_duration, middle_duration, total_duration
    )
    
    # 叠加角标数字人
    _overlay_corner_humans(paths, intro_duration, outro_duration)
    
    # 构建视频列表并拼接
    video_list = _build_corner_video_list(paths, intro_duration, middle_duration, outro_duration)
    
    if not video_list:
        # 如果没有片段，直接复制原视频
        shutil.copyfile(origin_video_path, paths.human_replaced_video)
    else:
        _concat_corner_videos(video_list, paths.human_replaced_video, use_transition=False)
    
    return paths.human_replaced_video


def human_pack_new_with_transition_corner(
    account_name: str,
    origin_video_path: str,
    audio_path: str,
    jsonpath: str,
    account_extra: Dict[str, Any],
) -> str:
    """角标模式 + 转场版本。"""
    paths = PathManager(origin_video_path)
    config = load_human_config(account_name, account_extra)
    
    # 角标模式使用不同的配置
    corner_config = account_extra.get(
        "human_config",
        {
            "path": config.path,
            "duration": 10,
            "end_duration": 10,
        },
    )
    intro_duration_account = corner_config.get("duration", 10)
    outro_duration_account = corner_config.get("end_duration", 10)
    human_video_source_path = corner_config.get("path", config.path)
    
    total_main_video_duration = safe_get_video_duration(origin_video_path)
    intro_duration = min(intro_duration_account, total_main_video_duration)
    outro_duration = min(outro_duration_account, total_main_video_duration - intro_duration)
    
    transition_types = account_extra.get("transition_types", ["fade"])
    transition_type = random.choice(transition_types) if transition_types else "fade"
    
    # 生成 intro / outro 段（同 corner 版本）
    if intro_duration > 0:
        extract_audio_segment(audio_path, paths.short_audio_intro, duration=intro_duration)
        post_human_generate(paths.short_audio_intro, human_video_source_path, paths.human_generate_intro)
        normalize_human_video(paths.human_generate_intro, paths.human_video_intro_final)
    
    if outro_duration > 0:
        audio_start_for_outro = safe_get_video_duration(audio_path) - outro_duration
        extract_audio_segment(audio_path, paths.short_audio_outro, start_time=audio_start_for_outro, duration=outro_duration)
        post_human_generate(paths.short_audio_outro, human_video_source_path, paths.human_generate_outro)
        normalize_human_video(paths.human_generate_outro, paths.human_video_outro_final)
    
    # 切主视频
    if intro_duration > 0:
        extract_video_segment(origin_video_path, paths.main_video_part1, duration=intro_duration)
    
    if outro_duration > 0:
        main_video_outro_start_time = total_main_video_duration - outro_duration
        extract_video_segment(origin_video_path, paths.main_video_part3, start_time=main_video_outro_start_time)
    
    middle_start_time = intro_duration
    middle_end_time = total_main_video_duration - outro_duration
    middle_duration = middle_end_time - middle_start_time
    if middle_duration > 0:
        extract_video_segment(origin_video_path, paths.main_video_part2, start_time=middle_start_time, duration=middle_duration)
    
    # 叠加角标
    if intro_duration > 0:
        overlay_corner_human(paths.main_video_part1, paths.human_video_intro_final, paths.part1_with_human)
    else:
        paths.part1_with_human = paths.main_video_part1
    
    if outro_duration > 0:
        overlay_corner_human(paths.main_video_part3, paths.human_video_outro_final, paths.part3_with_human)
    else:
        paths.part3_with_human = paths.main_video_part3
    
    # 使用 xfade 拼接所有片段
    video_list = []
    if intro_duration > 0:
        video_list.append(paths.part1_with_human)
    if middle_duration > 0:
        video_list.append(paths.main_video_part2)
    if outro_duration > 0:
        video_list.append(paths.part3_with_human)
    
    if not video_list:
        import shutil
        shutil.copyfile(origin_video_path, paths.human_replaced_video)
        return paths.human_replaced_video
    
    if len(video_list) == 1:
        import shutil
        shutil.copyfile(video_list[0], paths.human_replaced_video)
    else:
        concat_videos_with_xfade(video_list, paths.human_replaced_video, transition_type)
    
    return paths.human_replaced_video


__all__ = [
    "human_pack_new",
    "human_pack_new_with_transition",
    "human_pack_new_corner",
    "human_pack_new_with_transition_corner",
]

