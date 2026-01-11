"""视频生成流水线编排器。

负责协调各个服务完成视频生成的完整流程。
遵循依赖注入原则，通过构造函数接收服务实例。
"""
from typing import Any, Dict, List, Optional, Tuple

from utils.file_manager import FileManager

from config import path_manager, settings
from core.logging_config import setup_logging

from ..services.base import BaseService
from ..services.digital_human import DigitalHumanService
from ..services.image import ImageService
from ..services.subtitle import SubtitleService
from ..services.tts import TTSService
from ..services.video import VideoService
from .video_pipeline_steps import VideoGenerationSteps

logger = setup_logging("worker.pipeline")


class VideoGenerationPipeline:
    """视频生成流水线编排器。
    
    负责协调各个服务完成视频生成的完整流程。
    遵循依赖注入原则，通过构造函数接收服务实例。
    如果未提供服务实例，则创建默认实例（保持向后兼容）。
    
    Attributes:
        config: 配置对象
        file_manager: 文件管理器实例
        tts_service: TTS服务实例
        subtitle_service: 字幕服务实例
        digital_human_service: 数字人服务实例
        video_service: 视频服务实例
        image_service: 图像服务实例
        steps: 视频生成步骤编排器
    """
    
    def __init__(
        self,
        config: Optional[Any] = None,
        file_manager: Optional[FileManager] = None,
        tts_service: Optional[TTSService] = None,
        subtitle_service: Optional[SubtitleService] = None,
        digital_human_service: Optional[DigitalHumanService] = None,
        video_service: Optional[VideoService] = None,
        image_service: Optional[ImageService] = None,
    ) -> None:
        """初始化流水线。
        
        Args:
            config: 配置对象，如果为None则使用默认配置
            file_manager: 文件管理器实例，如果为None则创建默认实例
            tts_service: TTS服务实例，如果为None则创建默认实例
            subtitle_service: 字幕服务实例，如果为None则创建默认实例
            digital_human_service: 数字人服务实例，如果为None则创建默认实例
            video_service: 视频服务实例，如果为None则创建默认实例
            image_service: 图像服务实例，如果为None则创建默认实例
        """
        self.config = config or settings
        self.file_manager = file_manager or FileManager(path_manager)
        
        # 依赖注入：如果提供了服务实例则使用，否则创建默认实例
        # 这样可以保持向后兼容性，同时支持依赖注入
        self.tts_service = tts_service or TTSService(self.config)
        self.subtitle_service = subtitle_service or SubtitleService(self.config)
        self.digital_human_service = digital_human_service or DigitalHumanService(self.config)
        self.video_service = video_service or VideoService(self.config)
        self.image_service = image_service or ImageService(self.config)
        
        self.steps = VideoGenerationSteps(self)
    
    async def generate_all(
        self,
        title: str,
        content: str,
        language: str,
        prompt_gen_images: str,
        prompt_prefix: str,
        prompt_cover_image: str,
        logopath: Optional[str],
        reference_audio_path: Optional[str],
        message: str,
        speech_speed: float = 1.0,
        is_horizontal: bool = True,
        loras: Optional[List[Dict[str, Any]]] = None,
        extra: Optional[Dict[str, Any]] = None,
        topic: Optional[Any] = None,
        user_id: str = "",
        job_id: int = 0,
        platform: str = "edge",
        account: Optional[Any] = None,
    ) -> Optional[Tuple[str, str, str, str, str, str]]:
        """生成完整视频（使用新的服务模块）。
        
        Args:
            title: 视频标题
            content: 视频内容文本
            language: 语言代码
            prompt_gen_images: 图像生成提示词
            prompt_prefix: 提示词前缀
            prompt_cover_image: 封面图像提示词
            logopath: Logo路径（可选）
            reference_audio_path: 参考音频路径（可选）
            message: 消息描述
            speech_speed: 语音速度，默认1.0
            is_horizontal: 是否横向视频，默认True
            loras: LoRA配置列表（可选）
            extra: 额外配置字典（可选）
            topic: 主题对象（可选）
            user_id: 用户ID
            job_id: 任务ID
            platform: 平台类型，默认"edge"
            account: 账户对象（可选）
            
        Returns:
            Optional[Tuple[str, str, str, str, str, str]]: 
                如果成功，返回(logoed_video, subtitled_video, cover_image, 
                combined_video, srt_path, audio_path)元组；
                如果失败，返回None
                
        Raises:
            Exception: 视频生成过程中的任何异常
        """
        """
        生成完整视频（使用新的服务模块）
        
        Returns:
            (logoed_video, subtitled_video, cover_image, combined_video, srt_path, audio_path)
        """
        logger.info(f"[generate_all] 开始生成视频 job_id={job_id}, title={title}, language={language}, platform={platform}")
        
        try:
            # 解析参数
            topic_extra = topic.extra if topic and topic.extra else {}
            account_extra = account.extra if account and account.extra else {}
            extra = extra or {}
            loras = loras or []
            
            if not title:
                logger.warning(f"[generate_all] 标题为空，退出 job_id={job_id}")
                return None
            
            # 步骤1: 准备路径和配置
            paths = await self.steps.step_1_prepare_paths(title, user_id, job_id, is_horizontal)
            
            # 并行执行步骤2和步骤3
            import asyncio
            logger.info(f"[generate_all] 开始并行执行音频和图像生成 job_id={job_id}")

            # 步骤2: 生成音频和字幕
            task_audio = self.steps.step_2_generate_audio_and_subtitle(
                content=content,
                language=language,
                platform=platform,
                speech_speed=speech_speed,
                reference_audio_path=reference_audio_path,
                is_horizontal=is_horizontal,
                extra=extra,
                paths=paths,
                job_id=job_id,
            )
            
            # 步骤3: 生成图像描述和图像
            topic_extra['topic'] = topic.name if topic else ""
            task_images = self.steps.step_3_generate_images(
                content=content,
                prompt_gen_images=prompt_gen_images,
                prompt_prefix=prompt_prefix,
                prompt_cover_image=prompt_cover_image,
                topic_extra=topic_extra,
                loras=loras,
                paths=paths,
                job_id=job_id,
            )

            # 等待并行任务完成
            await asyncio.gather(task_audio, task_images)
            logger.info(f"[generate_all] 并行任务执行完成 job_id={job_id}")
            
            # 步骤4: 生成合并视频
            combined_video = await self.steps.step_4_generate_combined_video(
                account_extra=account_extra,
                paths=paths,
                job_id=job_id,
            )
            
            # 步骤5: 处理数字人（如果需要）
            human_video = await self.steps.step_5_process_digital_human(
                title=title,
                combined_video=combined_video,
                account_extra=account_extra,
                account=account,
                paths=paths,
                job_id=job_id,
            )
            if human_video:
                combined_video = human_video
            
            # 步骤6: 添加字幕和Logo
            logoed_video = await self.steps.step_6_add_subtitle_and_logo(
                logopath=logopath,
                account_extra=account_extra,
                account=account,
                is_horizontal=is_horizontal,
                combined_video=combined_video,
                paths=paths,
                job_id=job_id,
            )
            
            # 步骤7: H2V转换（如果需要）
            final_video = await self.steps.step_7_process_h2v(
                extra=extra,
                is_horizontal=is_horizontal,
                logoed_video=logoed_video,
                paths=paths,
                job_id=job_id,
            )
            
            logger.info(f"[generate_all] 生成完成 job_id={job_id}")
            return (
                final_video,
                paths["subtitled_video"],
                paths["cover_image"],
                combined_video,
                paths["srtpath"],
                paths["seedvc_mp3_audio"],
            )
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（视频生成错误等）
            logger.error(f"[generate_all] 生成视频时发生异常 job_id={job_id}, error={str(e)}", exc_info=True)
            raise
