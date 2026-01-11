"""SRT字幕生成器

负责生成SRT格式的字幕文件。
"""

from typing import List, Tuple

from pydub import AudioSegment

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.batch_synthesis.srt_generator")


def format_time(ms: int) -> str:
    """
    将毫秒数格式化为SRT时间格式 (HH:MM:SS,mmm)
    
    Args:
        ms: 毫秒数
        
    Returns:
        SRT格式的时间字符串
        
    Note:
        使用core.utils.time_formatter中的统一实现
    """
    from core.utils.time_formatter import format_time_ms_to_srt
    return format_time_ms_to_srt(ms)


class SRTGenerator:
    """SRT字幕生成器
    
    根据音频段和文本生成SRT格式的字幕文件。
    """
    
    def __init__(self, silence_duration_ms: int = 300):
        """
        初始化生成器
        
        Args:
            silence_duration_ms: 段之间的静音时长（毫秒）
        """
        self.silence_duration_ms = silence_duration_ms
    
    def generate_srt_entries(
        self,
        segments: List[Tuple[AudioSegment, str]],
        include_silence: bool = True,
    ) -> List[str]:
        """
        生成SRT条目列表
        
        Args:
            segments: (音频段, 文本) 元组列表，按顺序排列
            include_silence: 是否在段之间插入静音
            
        Returns:
            SRT条目字符串列表
        """
        if not segments:
            logger.warning("没有音频段，返回空SRT条目")
            return []
        
        srt_entries = []
        current_time_ms = 0
        
        for i, (segment_audio, text) in enumerate(segments):
            segment_duration_ms = len(segment_audio)
            
            start_time = format_time(current_time_ms)
            end_time = format_time(current_time_ms + segment_duration_ms)
            
            srt_entry = f"{i + 1}\n{start_time} --> {end_time}\n{text}\n"
            srt_entries.append(srt_entry)
            
            current_time_ms += segment_duration_ms
            
            # 在最后一段之前添加静音时长
            if include_silence and i < len(segments) - 1:
                current_time_ms += self.silence_duration_ms
        
        logger.info(f"生成 {len(srt_entries)} 个SRT条目")
        return srt_entries
    
    def write_srt_file(
        self,
        srt_entries: List[str],
        output_path: str,
        encoding: str = "utf-8",
    ) -> None:
        """
        写入SRT文件
        
        Args:
            srt_entries: SRT条目列表
            output_path: 输出文件路径
            encoding: 文件编码
        """
        logger.info(f"写入SRT文件: {output_path}")
        with open(output_path, 'w', encoding=encoding) as f:
            f.write("\n".join(srt_entries))
        logger.debug(f"SRT文件写入成功: {output_path}")

