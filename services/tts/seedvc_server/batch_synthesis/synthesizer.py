"""音频段合成器

负责单个音频段的合成任务，包括重试逻辑和错误处理。
"""

import os
import time
from typing import Optional, Tuple

from pydub import AudioSegment

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.batch_synthesis.synthesizer")


class AudioSegmentSynthesizer:
    """音频段合成器
    
    负责单个文本段的语音合成，包含重试机制和错误处理。
    """
    
    def __init__(
        self,
        client,
        max_retries: int = 10,
        retry_delay: float = 0.3,
    ):
        """
        初始化合成器
        
        Args:
            client: 语音合成客户端实例
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.client = client
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def synthesize_segment(
        self,
        index: int,
        text: str,
        reference_audio_path: str,
        voice: str,
        volume: int,
        speech_rate: int,
        pitch_rate: int,
        tts_type: Optional[str],
        diffusion_steps: int,
        length_adjust: float,
        inference_cfg_rate: float,
        temp_file_prefix: str = "temp_segment",
    ) -> Tuple[Optional[AudioSegment], str, int]:
        """
        合成单个音频段
        
        Args:
            index: 段索引
            text: 要合成的文本
            reference_audio_path: 参考音频路径
            voice: 语音标识
            volume: 音量
            speech_rate: 语速
            pitch_rate: 音调
            tts_type: TTS类型
            diffusion_steps: 扩散步数
            length_adjust: 长度调整
            inference_cfg_rate: 推理配置率
            temp_file_prefix: 临时文件前缀
            
        Returns:
            (音频段, 文本内容, 索引) 元组，失败时音频段为None
        """
        temp_audio_file = f"{temp_file_prefix}_{index}.wav"
        
        for attempt in range(self.max_retries):
            logger.debug(
                f"合成音频段 {index+1}: '{text[:50]}...' "
                f"(尝试 {attempt + 1}/{self.max_retries})"
            )
            
            success = self.client.synthesize_voice(
                text=text,
                audio_file_path=reference_audio_path,
                voice=voice,
                output_file=temp_audio_file,
                volume=volume,
                speech_rate=speech_rate,
                pitch_rate=pitch_rate,
                tts_type=tts_type,
                diffusion_steps=diffusion_steps,
                length_adjust=length_adjust,
                inference_cfg_rate=inference_cfg_rate,
            )
            
            if success:
                try:
                    segment_audio = AudioSegment.from_wav(temp_audio_file)
                    os.remove(temp_audio_file)
                    logger.debug(f"音频段 {index+1} 合成成功")
                    return segment_audio, text, index
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, IOError, ValueError) as e:
                    # 文件IO错误或音频格式错误
                    logger.error(f"[synthesize_segment] 文件IO或音频格式错误，加载音频段 {index+1} 失败: {e}", exc_info=True)
                    if os.path.exists(temp_audio_file):
                        try:
                            os.remove(temp_audio_file)
                        except (OSError, PermissionError):
                            pass
                except Exception as e:
                    # 其他异常
                    logger.error(f"[synthesize_segment] 加载音频段 {index+1} 失败: {e}", exc_info=True)
                    if os.path.exists(temp_audio_file):
                        try:
                            os.remove(temp_audio_file)
                        except (OSError, PermissionError):
                            pass
            
            logger.warning(
                f"音频段 {index+1} 合成失败: '{text[:50]}...' "
                f"(尝试 {attempt + 1}/{self.max_retries})"
            )
            
            if os.path.exists(temp_audio_file):
                os.remove(temp_audio_file)
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        logger.error(
            f"音频段 {index+1} 合成失败，已达最大重试次数: '{text[:50]}...'"
        )
        return None, text, index

