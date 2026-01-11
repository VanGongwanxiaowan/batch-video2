"""音频组合器

负责将多个音频段组合成完整的音频文件。
"""

from typing import List, Tuple

from pydub import AudioSegment

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.batch_synthesis.combiner")


class AudioCombiner:
    """音频组合器
    
    负责将多个音频段组合成完整音频，并插入静音间隔。
    """
    
    def __init__(self, silence_duration_ms: int = 300):
        """
        初始化组合器
        
        Args:
            silence_duration_ms: 段之间的静音时长（毫秒）
        """
        self.silence_duration_ms = silence_duration_ms
    
    def combine_segments(
        self,
        segments: List[Tuple[AudioSegment, str]],
        include_silence: bool = True,
    ) -> AudioSegment:
        """
        组合多个音频段
        
        Args:
            segments: (音频段, 文本) 元组列表，按顺序排列
            include_silence: 是否在段之间插入静音
            
        Returns:
            组合后的音频段
        """
        if not segments:
            logger.warning("没有音频段需要组合，返回空音频")
            return AudioSegment.empty()
        
        combined_audio = AudioSegment.empty()
        
        for i, (segment_audio, _) in enumerate(segments):
            combined_audio += segment_audio
            
            # 在最后一段之前插入静音
            if include_silence and i < len(segments) - 1:
                silence = AudioSegment.silent(duration=self.silence_duration_ms)
                combined_audio += silence
        
        logger.info(f"成功组合 {len(segments)} 个音频段，总时长: {len(combined_audio)}ms")
        return combined_audio
    
    def export_audio(
        self,
        audio: AudioSegment,
        output_path: str,
        format: str = "wav",
    ) -> None:
        """
        导出音频文件
        
        Args:
            audio: 要导出的音频段
            output_path: 输出路径
            format: 音频格式
        """
        logger.info(f"导出音频文件: {output_path} (格式: {format})")
        audio.export(output_path, format=format)
        logger.debug(f"音频文件导出成功: {output_path}")

