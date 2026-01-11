"""
字幕处理模块
负责字幕文件的格式转换和处理
"""
import pysrt
from opencc import OpenCC

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.subtitle_handler")


class SubtitleHandler:
    """字幕处理器"""
    
    def __init__(self) -> None:
        """初始化字幕处理器"""
        self._converter = None
    
    def convert_to_traditional(self, srtpath: str, job_id: int = 0) -> None:
        """
        将字幕转换为繁体中文
        
        Args:
            srtpath: 字幕文件路径
            job_id: 任务ID
        """
        logger.info(
            f"[convert_subtitle_to_traditional] 开始转换字幕为繁体中文 "
            f"job_id={job_id}"
        )
        
        if self._converter is None:
            self._converter = OpenCC("s2tw")
        
        subs = pysrt.open(srtpath, encoding="utf-8")
        logger.info(
            f"[convert_subtitle_to_traditional] 打开字幕文件 "
            f"job_id={job_id}, subs_count={len(subs)}"
        )
        
        for sub in subs:
            sub.text = self._converter.convert(sub.text)
        
        subs.save(srtpath, encoding="utf-8")
        logger.info(
            f"[convert_subtitle_to_traditional] 字幕转换为繁体中文完成 "
            f"job_id={job_id}"
        )


# 创建全局实例
subtitle_handler = SubtitleHandler()

