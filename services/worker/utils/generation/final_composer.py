"""
最终合成模块
负责为最终视频添加字幕和Logo
"""
import os
from typing import Any, Dict, Optional

from gushi import videocombine, videocombineallwithlogo

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.final_composer")


class FinalComposer:
    """最终视频合成器"""
    
    def add_subtitle_and_logo_to_final_video(
        self,
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
        """
        为最终视频添加字幕和Logo
        
        Args:
            srtpath: 字幕文件路径
            seedvc_mp3_audio: 音频文件路径
            combined_video: 合并后的视频路径
            logopath: Logo文件路径
            is_horizontal: 是否横向视频
            account_extra: 账号额外配置
            account: 账号对象
            paths: 路径字典
            job_id: 任务ID
            
        Returns:
            最终视频路径
        """
        logger.info(
            f"[add_subtitle_and_logo] 检查logo路径 job_id={job_id}, "
            f"logopath={logopath}"
        )
        
        subtitle_background = account_extra.get("subtitle_background", "#578B2E")
        
        if logopath and os.path.exists(logopath):
            logger.info(
                f"[add_subtitle_and_logo] 使用logo合成视频 job_id={job_id}"
            )
            videocombineallwithlogo(
                srtpath,
                seedvc_mp3_audio,
                combined_video,
                paths["logoed_video"],
                logopath,
                is_horizontal,
                background_hex_color=subtitle_background,
                account_name=account.username,
            )
            logger.info(
                f"[add_subtitle_and_logo] logo视频合成完成 job_id={job_id}"
            )
            return paths["logoed_video"]
        else:
            logger.info(
                f"[add_subtitle_and_logo] 不使用logo合成视频 job_id={job_id}"
            )
            videocombine(
                srtpath,
                seedvc_mp3_audio,
                combined_video,
                paths["subtitled_video"],
                is_horizontal,
                background_hex_color=subtitle_background,
                account_name=account.username,
            )
            logger.info(
                f"[add_subtitle_and_logo] 视频合成完成 job_id={job_id}"
            )
            return paths["subtitled_video"]


# 创建全局实例
final_composer = FinalComposer()

