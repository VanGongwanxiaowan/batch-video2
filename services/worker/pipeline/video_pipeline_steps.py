"""视频生成流水线步骤函数

将 generate_all 方法拆分为多个独立的步骤函数，提高可测试性和可维护性。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 替换硬编码的 1360x768 分辨率
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import get_dimensions

logger = setup_logging("worker.pipeline.steps")


class VideoGenerationSteps:
    """视频生成步骤编排器"""
    
    def __init__(self, pipeline: Any) -> None:
        """
        初始化步骤编排器
        
        Args:
            pipeline: VideoGenerationPipeline 实例
        """
        self.pipeline = pipeline
        self.file_manager = pipeline.file_manager
        self.tts_service = pipeline.tts_service
        self.subtitle_service = pipeline.subtitle_service
        self.digital_human_service = pipeline.digital_human_service
        self.video_service = pipeline.video_service
        self.image_service = pipeline.image_service
    
    async def step_1_prepare_paths(
        self,
        title: str,
        user_id: str,
        job_id: int,
        is_horizontal: bool,
    ) -> Dict[str, str]:
        """
        步骤1: 准备路径和配置
        
        Returns:
            包含所有文件路径的字典
        """
        logger.info(f"[step_1] 准备路径和配置 job_id={job_id}")
        
        # 处理标题和用户ID
        title = title.replace(" ", "_").replace("+", "_")
        user_id = user_id.replace("-", "")

        # 使用统一的视频配置获取分辨率
        width, height = get_dimensions(is_horizontal=is_horizontal)

        # 创建任务目录
        job_dir = self.file_manager.get_job_directory(job_id, user_id, title)
        self.file_manager.ensure_directory(job_dir)
        
        # 设置文件路径
        return {
            "job_dir": job_dir,
            "seedvc_mp3_audio": str(job_dir / "seedvc.mp3"),
            "datajson_path": str(job_dir / "data.json"),
            "srtpath": str(job_dir / "data.srt"),
            "subtitled_video": str(job_dir / "subtitled.mp4"),
            "logoed_video": str(job_dir / "logoed.mp4"),
            "h2v_video": str(job_dir / "h2v.mp4"),
            "cover_image": str(job_dir / "0.png"),
            "width": width,
            "height": height,
        }
    
    async def step_2_generate_audio_and_subtitle(
        self,
        content: str,
        language: str,
        platform: str,
        speech_speed: float,
        reference_audio_path: Optional[str],
        is_horizontal: bool,
        extra: Dict[str, Any],
        paths: Dict[str, str],
        job_id: int,
    ) -> None:
        """步骤2: 生成音频和字幕"""
        logger.info(f"[step_2] 生成音频和字幕 job_id={job_id}")
        
        seedvc_mp3_audio = paths["seedvc_mp3_audio"]
        srtpath = paths["srtpath"]
        
        if os.path.exists(seedvc_mp3_audio) and os.path.exists(srtpath):
            logger.info(f"[step_2] 音频和字幕已存在，跳过生成 job_id={job_id}")
            return
        
        # 使用TTS服务生成音频和字幕
        tts_result = await self.tts_service.synthesize(
            text=content,
            output_audio_path=seedvc_mp3_audio,
            output_srt_path=srtpath,
            language=language,
            platform=platform,
            reference_audio_path=reference_audio_path,
            speech_rate=speech_speed,
            job_id=job_id,
        )
        
        if not tts_result.get("success"):
            raise Exception(f"TTS生成失败: {tts_result.get('error')}")
        
        # 处理字幕
        square = self.subtitle_service.is_square_language(language)
        subtitle_result = await self.subtitle_service.process({
            "srt_file_path": srtpath,
            "square": square,
            "is_horizontal": is_horizontal,
            "convert_traditional": extra.get("traditional_subtitle", False),
        })
        
        if not subtitle_result.get("success"):
            raise Exception(f"字幕处理失败: {subtitle_result.get('error')}")
        
        # 如果需要转换为繁体中文
        if extra.get("traditional_subtitle", False):
            self.subtitle_service.convert_to_traditional(srtpath)
    
    async def step_3_generate_images(
        self,
        content: str,
        prompt_gen_images: str,
        prompt_prefix: str,
        prompt_cover_image: str,
        topic_extra: Dict[str, Any],
        loras: List[Dict[str, Any]],
        paths: Dict[str, str],
        job_id: int,
    ) -> None:
        """步骤3: 生成图像描述和图像"""
        logger.info(f"[step_3] 生成图像描述和图像 job_id={job_id}")
        
        srtpath = paths["srtpath"]
        datajson_path = paths["datajson_path"]
        job_dir = paths["job_dir"]
        width = paths["width"]
        height = paths["height"]
        
        # 生成图像描述
        image_desc_result = await self.image_service.generate_image_descriptions(
            srt_path=srtpath,
            data_json_path=datajson_path,
            prompt_gen_images=prompt_gen_images,
            prompt_prefix=prompt_prefix,
            prompt_cover_image=prompt_cover_image,
            model="gemini-2.5-flash",
            topic_extra=topic_extra,
        )
        
        if not image_desc_result.get("success"):
            raise Exception(f"图像描述生成失败: {image_desc_result.get('error')}")
        
        # 生成Actor图像（如果需要）
        if topic_extra.get("generate_type", "none") == "same":
            logger.info(f"[step_3] 生成类型为same，开始生成actor job_id={job_id}")
            actor_result = await self.image_service.generate_actor_images(
                base_path=str(job_dir),
                content=content,
                loras=loras,
            )
            if not actor_result.get("success"):
                logger.warning(f"[step_3] Actor生成失败 job_id={job_id}")
        
        # 生成图像
        topic_extra['topic'] = topic_extra.get('topic', '')
        image_result = await self.image_service.generate_images(
            base_path=str(job_dir),
            width=width,
            height=height,
            loras=loras,
            topic_extra=topic_extra,
        )
        
        if not image_result.get("success"):
            raise Exception(f"图像生成失败: {image_result.get('error')}")
    
    async def step_4_generate_combined_video(
        self,
        account_extra: Dict[str, Any],
        paths: Dict[str, str],
        job_id: int,
    ) -> str:
        """步骤4: 生成合并视频"""
        logger.info(f"[step_4] 生成合并视频 job_id={job_id}")
        
        srtpath = paths["srtpath"]
        job_dir = paths["job_dir"]
        width = paths["width"]
        height = paths["height"]
        
        enable_transition = account_extra.get("enable_transition", False)
        transition_types = account_extra.get("transition_types", ["fade"])
        
        # 生成分镜视频
        scene_video_result = await self.video_service.create_scene_videos(
            srt_path=srtpath,
            width=width,
            height=height,
            over=1 if enable_transition else 0,
        )
        
        if not scene_video_result.get("success"):
            raise Exception(f"分镜视频生成失败: {scene_video_result.get('error')}")
        
        # 合并视频
        combined_video = await self.video_service.concat_scene_videos(
            srt_path=srtpath,
            base_path=str(job_dir),
            enable_transition=enable_transition,
            transition_types=transition_types,
        )
        
        if not combined_video:
            raise Exception("视频合并失败")
        
        return combined_video
    
    async def step_5_process_digital_human(
        self,
        title: str,
        combined_video: str,
        account_extra: Dict[str, Any],
        account: Any,
        paths: Dict[str, str],
        job_id: int,
    ) -> Optional[str]:
        """步骤5: 处理数字人（如果需要）"""
        human = "数字人" in title
        if not human:
            return None
        
        logger.info(f"[step_5] 处理数字人视频 job_id={job_id}")
        
        seedvc_mp3_audio = paths["seedvc_mp3_audio"]
        datajson_path = paths["datajson_path"]
        
        human_insertion_mode = account_extra.get("human_insertion_mode", "fullscreen")
        enable_human_transition = account_extra.get("enable_transition", False)
        
        human_result = await self.digital_human_service.generate_digital_human(
            account_name=account.username if account else "",
            origin_video_path=combined_video,
            audio_path=seedvc_mp3_audio,
            jsonpath=datajson_path,
            account_extra=account_extra,
            mode=human_insertion_mode,
            enable_transition=enable_human_transition,
        )
        
        if human_result:
            logger.info(f"[step_5] 数字人视频处理完成 job_id={job_id}")
            return human_result
        
        return None
    
    async def step_6_add_subtitle_and_logo(
        self,
        logopath: Optional[str],
        account_extra: Dict[str, Any],
        account: Any,
        is_horizontal: bool,
        combined_video: str,
        paths: Dict[str, str],
        job_id: int,
    ) -> str:
        """步骤6: 添加字幕和Logo"""
        logger.info(f"[step_6] 添加字幕和Logo job_id={job_id}")
        
        srtpath = paths["srtpath"]
        seedvc_mp3_audio = paths["seedvc_mp3_audio"]
        logoed_video = paths["logoed_video"]
        subtitled_video = paths["subtitled_video"]
        
        background_color = account_extra.get("subtitle_background", "#578B2E")
        account_name = account.username if account else ""
        
        if logopath and os.path.exists(logopath):
            logo_result = await self.video_service.add_logo(
                srt_path=srtpath,
                audio_path=seedvc_mp3_audio,
                combined_video=combined_video,
                output_video=logoed_video,
                logo_path=logopath,
                is_horizontal=is_horizontal,
                background_hex_color=background_color,
                account_name=account_name,
            )
            if not logo_result.get("success"):
                raise Exception(f"添加Logo失败: {logo_result.get('error')}")
            return logoed_video
        else:
            subtitle_result = await self.video_service.add_subtitle_and_audio(
                srt_path=srtpath,
                audio_path=seedvc_mp3_audio,
                combined_video=combined_video,
                output_video=subtitled_video,
                is_horizontal=is_horizontal,
                background_hex_color=background_color,
                account_name=account_name,
            )
            if not subtitle_result.get("success"):
                raise Exception(f"添加字幕失败: {subtitle_result.get('error')}")
            return subtitled_video
    
    async def step_7_process_h2v(
        self,
        extra: Dict[str, Any],
        is_horizontal: bool,
        logoed_video: str,
        paths: Dict[str, str],
        job_id: int,
    ) -> str:
        """步骤7: H2V转换（如果需要）"""
        if not (extra.get("h2v", False) and is_horizontal):
            return logoed_video
        
        logger.info(f"[step_7] 开始h2v转换 job_id={job_id}")
        
        h2v_video = paths["h2v_video"]
        
        h2v_result = await self.video_service.convert_h2v(
            index_text=extra.get("index_text", ""),
            title_text=extra.get("title_text", ""),
            desc_text=extra.get("desc_text", ""),
            audio=extra.get("audio", ""),
            input_path=logoed_video,
            output_path=h2v_video,
        )
        
        if h2v_result.get("success"):
            return h2v_result.get("video_path")
        
        return logoed_video

