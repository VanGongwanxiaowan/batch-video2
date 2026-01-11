"""
视频生成步骤模块
负责分镜视频生成、合并和H2V转换
"""
from typing import Dict, List, Optional

from gushi import (
    concat_videos,
    concat_videos_with_transitions,
    generate_video,
    h2v,
)

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.video_generator_steps")


class VideoGeneratorSteps:
    """视频生成步骤处理器"""
    
    def generate_combined_video(
        self,
        srtpath: str,
        assrtpath: str,
        width: int,
        height: int,
        enable_transition: bool,
        transition_types: List[str],
        job_id: int = 0,
    ) -> str:
        """
        生成合并后的视频
        
        Args:
            srtpath: 字幕文件路径
            assrtpath: 资源路径
            width: 视频宽度
            height: 视频高度
            enable_transition: 是否启用转场效果
            transition_types: 转场类型列表
            job_id: 任务ID
            
        Returns:
            合并后的视频路径
        """
        logger.info(
            f"[generate_combined_video] 检查转场效果设置 "
            f"job_id={job_id}, enable_transition={enable_transition}"
        )
        
        if enable_transition:
            logger.info(
                f"[generate_combined_video] 启用转场效果，生成视频 "
                f"job_id={job_id}"
            )
            generate_video(srtpath, width, height, 1)
            logger.info(
                f"[generate_combined_video] 视频生成完成，开始合并视频（带转场） "
                f"job_id={job_id}"
            )
            combined_video = concat_videos_with_transitions(
                srtpath, assrtpath, transition_types
            )
            logger.info(
                f"[generate_combined_video] 视频合并完成（带转场） "
                f"job_id={job_id}"
            )
        else:
            logger.info(
                f"[generate_combined_video] 未启用转场效果，生成视频 "
                f"job_id={job_id}"
            )
            generate_video(srtpath, width, height, 0)
            logger.info(
                f"[generate_combined_video] 视频生成完成，开始合并视频 "
                f"job_id={job_id}"
            )
            combined_video = concat_videos(srtpath, assrtpath)
            logger.info(
                f"[generate_combined_video] 视频合并完成 job_id={job_id}"
            )
        
        return combined_video
    
    def process_h2v_conversion(
        self,
        extra: Dict,
        is_horizontal: bool,
        logoed_video: str,
        h2v_video_path: str,
        job_id: int = 0,
    ) -> str:
        """
        处理h2v转换（横向转竖向）
        
        Args:
            extra: 额外配置字典
            is_horizontal: 是否横向视频
            logoed_video: 带Logo的视频路径
            h2v_video_path: H2V输出视频路径
            job_id: 任务ID
            
        Returns:
            转换后的视频路径
        """
        if extra.get("h2v", False) and is_horizontal:
            logger.info(f"[process_h2v] 需要h2v转换 job_id={job_id}")
            index_text = extra.get("index_text", "")
            title_text = extra.get("title_text", "")
            desc_text = extra.get("desc_text", "")
            audio = extra.get("audio", "")
            
            h2v(index_text, title_text, desc_text, audio, logoed_video, h2v_video_path)
            logger.info(f"[process_h2v] h2v转换完成 job_id={job_id}")
            return h2v_video_path
        
        return logoed_video


# 创建全局实例
video_generator_steps = VideoGeneratorSteps()

