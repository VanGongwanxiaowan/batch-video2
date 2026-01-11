"""
[LEGACY MODULE] 此模块已被重构为 pipeline.video_pipeline.VideoGenerationPipeline

为了保持向后兼容，此文件保留原有函数接口，但建议新代码使用新模块。
"""

import os
from typing import TYPE_CHECKING, Any, Dict, Optional

from utils.video_generation_steps import (
    SQUARE_WORDS_LIST,
    add_subtitle_and_logo_to_final_video,
    calculate_points,
    convert_subtitle_to_traditional,
    generate_audio_and_subtitle,
    generate_combined_video,
    generate_images,
    prepare_paths_and_config,
    process_digital_human,
    process_h2v_conversion,
)

if TYPE_CHECKING:
    from utils.generation.video_generation_config import VideoGenerationConfig

from core.logging_config import setup_logging

# 统一日志记录器（legacy，仅保留给旧脚本使用）
logger = setup_logging("worker.pipeline_legacy")

# 文件图片资源保存路径
from config import path_manager, settings

ASSERTSPATH = str(path_manager.worker_assets_dir)


def human_pack_new_corner(
    account_name: str, 
    origin_video_path: str, 
    audio_path: str, 
    jsonpath: str, 
    account_extra: Dict[str, Any]
) -> Optional[str]:
    """Legacy wrapper for backward compatibility; implementation moved to digital_human.human_pipeline.
    
    Args:
        account_name: 账户名称
        origin_video_path: 原始视频路径
        audio_path: 音频路径
        jsonpath: JSON文件路径
        account_extra: 账户额外配置
        
    Returns:
        Optional[str]: 生成的视频路径，失败返回None
    """
    from services.worker.services.digital_human.human_pipeline import human_pack_new_corner as _impl

    return _impl(account_name, origin_video_path, audio_path, jsonpath, account_extra)


def human_pack_new_with_transition_corner(
    account_name: str, 
    origin_video_path: str, 
    audio_path: str, 
    jsonpath: str, 
    account_extra: Dict[str, Any]
) -> Optional[str]:
    """Legacy wrapper for backward compatibility; implementation moved to digital_human.human_pipeline.
    
    Args:
        account_name: 账户名称
        origin_video_path: 原始视频路径
        audio_path: 音频路径
        jsonpath: JSON文件路径
        account_extra: 账户额外配置
        
    Returns:
        Optional[str]: 生成的视频路径，失败返回None
    """
    from services.worker.services.digital_human.human_pipeline import (
        human_pack_new_with_transition_corner as _impl,
    )
    return _impl(account_name, origin_video_path, audio_path, jsonpath, account_extra)


# 以下工具函数已迁移或可直接使用：
# - get_video_duration: 直接使用 core.utils.ffmpeg.get_video_duration
# - ensure_path: 直接使用 os.makedirs(path, exist_ok=True)
# - ensure_assrt_path: 已迁移到 utils.file_manager.FileManager


# 向后兼容：导出 square_words_list
square_words_list = SQUARE_WORDS_LIST

# 扣点逻辑


def generate_all(
    title,
    content,
    language,
    prompt_gen_images,
    prompt_prefix,
    prompt_cover_image,
    logopath,
    reference_audio_path,
    message,
    speech_speed=1,
    is_horizontal=True,
    loras=None,
    extra=None,
    topic=None,
    user_id="",
    job_id=0,
    platform="edge",
    account=None,
):
    """
    [DEPRECATED] 此函数已被 VideoGenerationPipeline.generate_all 替代。
    
    此函数保留仅用于向后兼容，新代码应使用：
    - services.worker.pipeline.video_pipeline.VideoGenerationPipeline.generate_all
    
    该函数将在未来版本中移除。
    
    此函数已重构为使用配置数据类和模块化的步骤函数，代码更清晰、更易维护。
    
    Args:
        title: 视频标题
        content: 视频内容文本
        language: 语言代码
        prompt_gen_images: 图像生成提示词
        prompt_prefix: 提示词前缀
        prompt_cover_image: 封面图像提示词
        logopath: Logo文件路径
        reference_audio_path: 参考音频路径
        message: 消息内容（已废弃）
        speech_speed: 语音速度，默认1
        is_horizontal: 是否横向视频，默认True
        loras: LoRA模型列表，默认None（内部转换为空列表）
        extra: 额外配置字典，默认None（内部转换为空字典）
        topic: 主题对象，默认None
        user_id: 用户ID，默认空字符串
        job_id: 任务ID，默认0
        platform: TTS平台，默认"edge"
        account: 账户对象，默认None
        
    Returns:
        Tuple[str, str, str, str, str, str]: 
            (logoed_video, subtitled_video, input_image_file, combined_video, srtpath, seedvc_mp3_audio)
    """
    from utils.generation.video_generation_config import VideoGenerationConfig

    # 使用配置数据类封装参数
    config = VideoGenerationConfig(
        title=title,
        content=content,
        language=language,
        prompt_gen_images=prompt_gen_images,
        prompt_prefix=prompt_prefix,
        prompt_cover_image=prompt_cover_image,
        logopath=logopath,
        reference_audio_path=reference_audio_path,
        message=message,
        speech_speed=speech_speed,
        is_horizontal=is_horizontal,
        loras=loras or [],
        extra=extra or {},
        topic=topic,
        user_id=user_id,
        job_id=job_id,
        platform=platform,
        account=account,
    )
    
    return _generate_all_with_config(config)


def _generate_all_with_config(config: "VideoGenerationConfig") -> tuple:  # type: ignore
    """
    使用配置对象生成视频的内部实现函数
    
    此函数将原来的 generate_all 逻辑重构为使用配置对象，
    提高了代码的可维护性和可测试性。
    
    Args:
        config: 视频生成配置对象
        
    Returns:
        Tuple[str, str, str, str, str, str]: 
            (logoed_video, subtitled_video, input_image_file, combined_video, srtpath, seedvc_mp3_audio)
            
    Raises:
        SystemExit, KeyboardInterrupt: 系统退出异常直接抛出
        Exception: 其他异常会记录日志后抛出
    """
    from utils.generation.video_generation_config import VideoGenerationConfig
    
    logger.info(
        f"[generate_all] 开始生成视频 "
        f"job_id={config.job_id}, title={config.title}, "
        f"language={config.language}, platform={config.platform}"
    )
    
    try:
        # 验证标题
        if not config.title:
            logger.warning(f"[generate_all] 标题为空，退出 job_id={config.job_id}")
            return None
        
        # 准备路径和配置
        paths = prepare_paths_and_config(
            config.title, config.user_id, ASSERTSPATH, config.is_horizontal
        )
        assrtpath = paths["assrtpath"]
        width = paths["width"]
        height = paths["height"]
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(paths["seedvc_audio"]), exist_ok=True)
        
        # 生成音频和字幕
        generate_audio_and_subtitle(
            content=config.content,
            language=config.language,
            platform=config.platform,
            speech_speed=config.speech_speed,
            reference_audio_path=config.reference_audio_path,
            output_base_name=paths["seedvc_audio"],
            srtpath=paths["srtpath"],
            seedvc_mp3_audio=paths["seedvc_mp3_audio"],
            is_horizontal=config.is_horizontal,
            job_id=config.job_id,
        )
        
        # 转换繁体字幕（如果需要）
        if config.should_convert_to_traditional():
            convert_subtitle_to_traditional(paths["srtpath"], config.job_id)
        
        # 准备主题额外配置
        topic_extra = config.get_topic_extra()
        topic_extra['topic'] = config.get_topic_name()
        
        # 生成图片
        generate_images(
            srtpath=paths["srtpath"],
            datajson_path=paths["datajson_path"],
            assrtpath=assrtpath,
            prompt_gen_images=config.prompt_gen_images,
            prompt_prefix=config.prompt_prefix,
            prompt_cover_image=config.prompt_cover_image,
            width=width,
            height=height,
            loras=config.loras,
            topic_extra=topic_extra,
            content=config.content,
            job_id=config.job_id,
        )
        
        # 生成合并视频
        enable_transition, transition_types = config.get_transition_config()
        combined_video = generate_combined_video(
            srtpath=paths["srtpath"],
            assrtpath=assrtpath,
            width=width,
            height=height,
            enable_transition=enable_transition,
            transition_types=transition_types,
            job_id=config.job_id,
        )
        
        # 处理数字人
        account_extra = config.get_account_extra()
        human_video_path = process_digital_human(
            title=config.title,
            combined_video=combined_video,
            seedvc_mp3_audio=paths["seedvc_mp3_audio"],
            datajson_path=paths["datajson_path"],
            account_extra=account_extra,
            account=config.account,
            job_id=config.job_id,
        )
        if human_video_path:
            combined_video = human_video_path
        
        # 添加字幕和Logo
        logoed_video = add_subtitle_and_logo_to_final_video(
            srtpath=paths["srtpath"],
            seedvc_mp3_audio=paths["seedvc_mp3_audio"],
            combined_video=combined_video,
            logopath=config.logopath,
            is_horizontal=config.is_horizontal,
            account_extra=account_extra,
            account=config.account,
            paths=paths,
            job_id=config.job_id,
        )
        
        # 处理h2v转换
        logoed_video = process_h2v_conversion(
            extra=config.extra,
            is_horizontal=config.is_horizontal,
            logoed_video=logoed_video,
            paths=paths,
            job_id=config.job_id,
        )
        
        # 计算点数
        counts = calculate_points(assrtpath, config.content)
        logger.info(f"[generate_all] 点数计算完成 job_id={config.job_id}, counts={counts}")
        
        # 封面图片路径
        input_image_file = os.path.join(assrtpath, "0.png")
        
        logger.info(f"[generate_all] 生成完成，返回文件路径 job_id={config.job_id}")
        return (
            logoed_video,
            paths["subtitled_video"],
            input_image_file,
            combined_video,
            paths["srtpath"],
            paths["seedvc_mp3_audio"],
        )

    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（视频生成错误等）
        logger.error(
            f"[generate_all] 生成视频时发生异常 job_id={config.job_id}, error={str(e)}",
            exc_info=True
        )
        import traceback
        logger.error(f"[generate_all] 异常堆栈 job_id={config.job_id}\n{traceback.format_exc()}")
        raise
