"""
数字人处理模块
负责数字人视频的生成和处理
"""
from typing import Any, Dict, Optional

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.digital_human_handler")


class DigitalHumanHandler:
    """数字人处理器"""
    
    def process_digital_human(
        self,
        title: str,
        combined_video: str,
        seedvc_mp3_audio: str,
        datajson_path: str,
        account_extra: Dict[str, Any],
        account: Any,
        job_id: int = 0,
    ) -> Optional[str]:
        """
        处理数字人视频
        
        Args:
            title: 视频标题
            combined_video: 合并后的视频路径
            seedvc_mp3_audio: 音频文件路径
            datajson_path: 数据JSON文件路径
            account_extra: 账号额外配置
            account: 账号对象
            job_id: 任务ID
            
        Returns:
            数字人视频路径，如果不需要处理则返回None
        """
        human = "数字人" in title
        logger.info(
            f"[process_digital_human] 检查是否需要数字人处理 "
            f"job_id={job_id}, human={human}"
        )
        
        if not human:
            return None
        
        enable_human_transition = account_extra.get("enable_transition", False)
        human_insertion_mode = account_extra.get("human_insertion_mode", "fullscreen")
        logger.info(
            f"[process_digital_human] 数字人转场效果设置 "
            f"job_id={job_id}, enable_human_transition={enable_human_transition}, "
            f"mode={human_insertion_mode}"
        )
        
        if human_insertion_mode == "corner":
            return self._process_corner_mode(
                account, combined_video, seedvc_mp3_audio,
                datajson_path, account_extra, enable_human_transition, job_id
            )
        else:
            logger.warning(
                f"[process_digital_human] fullscreen 数字人处理已迁移到 "
                f"VideoGenerationPipeline + DigitalHumanService，"
                f"当前 legacy generate_all 不再直接调用 human_pack_new*_fullscreen 实现 "
                f"job_id={job_id}"
            )
            return None
    
    def _process_corner_mode(
        self,
        account: Any,
        combined_video: str,
        seedvc_mp3_audio: str,
        datajson_path: str,
        account_extra: Dict[str, Any],
        enable_human_transition: bool,
        job_id: int,
    ) -> Optional[str]:
        """处理角落模式的数字人"""
        from pipe_line import (
            human_pack_new_corner,
            human_pack_new_with_transition_corner,
        )
        
        if enable_human_transition:
            logger.info(
                f"[process_digital_human] 调用human_pack_new_with_transition_corner "
                f"job_id={job_id}"
            )
            human_video_path = human_pack_new_with_transition_corner(
                account.username,
                combined_video,
                seedvc_mp3_audio,
                datajson_path,
                account_extra,
            )
        else:
            logger.info(
                f"[process_digital_human] 调用human_pack_new_corner "
                f"job_id={job_id}"
            )
            human_video_path = human_pack_new_corner(
                account.username,
                combined_video,
                seedvc_mp3_audio,
                datajson_path,
                account_extra,
            )
        
        if human_video_path:
            logger.info(
                f"[process_digital_human] 数字人视频处理成功 job_id={job_id}"
            )
            return human_video_path
        else:
            logger.warning(
                f"[process_digital_human] 数字人视频处理失败 job_id={job_id}"
            )
            return None


# 创建全局实例
digital_human_handler = DigitalHumanHandler()

