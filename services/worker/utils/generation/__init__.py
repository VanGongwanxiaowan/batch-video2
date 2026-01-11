"""
视频生成步骤模块
提供视频生成流程的各个步骤函数
"""
from typing import Any, Dict, List, Optional

from .audio_generator import AudioGenerator, audio_generator
from .digital_human_handler import DigitalHumanHandler, digital_human_handler
from .final_composer import FinalComposer, final_composer
from .generation_utils import calculate_points
from .image_generator_steps import ImageGeneratorSteps, image_generator_steps
from .path_config import SQUARE_WORDS_LIST, PathConfig
from .subtitle_handler import SubtitleHandler, subtitle_handler
from .video_generation_config import VideoGenerationConfig
from .video_generator_steps import VideoGeneratorSteps, video_generator_steps


# 向后兼容：导出函数接口
def prepare_paths_and_config(
    title: str, 
    user_id: str, 
    assertspath: str, 
    is_horizontal: bool
) -> Dict[str, Any]:
    """准备所有文件路径和配置
    
    Args:
        title: 标题
        user_id: 用户ID
        assertspath: 资源路径
        is_horizontal: 是否横向
        
    Returns:
        Dict[str, Any]: 路径配置字典
    """
    return PathConfig.prepare_paths_and_config(title, user_id, assertspath, is_horizontal)

def generate_audio_and_subtitle(
    content: str,
    language: str,
    platform: str,
    speech_speed: float,
    reference_audio_path: str,
    output_base_name: str,
    srtpath: str,
    seedvc_mp3_audio: str,
    is_horizontal: bool,
    job_id: int = 0,
) -> None:
    """生成音频和字幕文件"""
    audio_generator.generate_audio_and_subtitle(
        content, language, platform, speech_speed,
        reference_audio_path, output_base_name, srtpath,
        seedvc_mp3_audio, is_horizontal, job_id
    )

def convert_subtitle_to_traditional(srtpath: str, job_id: int = 0) -> None:
    """将字幕转换为繁体中文"""
    subtitle_handler.convert_to_traditional(srtpath, job_id)

def generate_images(
    srtpath: str,
    datajson_path: str,
    assrtpath: str,
    prompt_gen_images: str,
    prompt_prefix: str,
    prompt_cover_image: str,
    width: int,
    height: int,
    loras: List[Dict[str, Any]],
    topic_extra: Dict[str, Any],
    content: str,
    job_id: int = 0,
) -> None:
    """生成图片描述和图片"""
    image_generator_steps.generate_images(
        srtpath, datajson_path, assrtpath, prompt_gen_images,
        prompt_prefix, prompt_cover_image, width, height,
        loras, topic_extra, content, job_id
    )

def generate_combined_video(
    srtpath: str,
    assrtpath: str,
    width: int,
    height: int,
    enable_transition: bool,
    transition_types: List[str],
    job_id: int = 0,
) -> str:
    """生成合并后的视频"""
    return video_generator_steps.generate_combined_video(
        srtpath, assrtpath, width, height,
        enable_transition, transition_types, job_id
    )

def process_digital_human(
    title: str,
    combined_video: str,
    seedvc_mp3_audio: str,
    datajson_path: str,
    account_extra: Dict[str, Any],
    account: Any,
    job_id: int = 0,
) -> Optional[str]:
    """处理数字人视频"""
    return digital_human_handler.process_digital_human(
        title, combined_video, seedvc_mp3_audio,
        datajson_path, account_extra, account, job_id
    )

def add_subtitle_and_logo_to_final_video(
    srtpath: str,
    seedvc_mp3_audio: str,
    combined_video: str,
    logopath: Optional[str],
    is_horizontal: bool,
    account_extra: Dict[str, Any],
    account: Any,
    paths: Dict[str, str],
    job_id: int = 0,
) -> str:
    """为最终视频添加字幕和Logo"""
    return final_composer.add_subtitle_and_logo_to_final_video(
        srtpath, seedvc_mp3_audio, combined_video, logopath,
        is_horizontal, account_extra, account, paths, job_id
    )

def process_h2v_conversion(
    extra: Dict[str, Any],
    is_horizontal: bool,
    logoed_video: str,
    paths: Dict[str, str],
    job_id: int = 0,
) -> str:
    """处理h2v转换（横向转竖向）"""
    return video_generator_steps.process_h2v_conversion(
        extra, is_horizontal, logoed_video, paths.get("h2v_video", ""), job_id
    )

__all__ = [
    # 类
    'PathConfig',
    'AudioGenerator',
    'SubtitleHandler',
    'ImageGeneratorSteps',
    'VideoGeneratorSteps',
    'DigitalHumanHandler',
    'FinalComposer',
    'VideoGenerationConfig',
    # 实例
    'audio_generator',
    'subtitle_handler',
    'image_generator_steps',
    'video_generator_steps',
    'digital_human_handler',
    'final_composer',
    # 函数
    'prepare_paths_and_config',
    'generate_audio_and_subtitle',
    'convert_subtitle_to_traditional',
    'generate_images',
    'generate_combined_video',
    'process_digital_human',
    'add_subtitle_and_logo_to_final_video',
    'process_h2v_conversion',
    'calculate_points',
    # 常量
    'SQUARE_WORDS_LIST',
]

