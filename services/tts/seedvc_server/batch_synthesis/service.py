"""批量语音合成服务

编排整个批量语音合成流程，协调各个组件的工作。
"""

import concurrent.futures
import os
from pathlib import Path
from typing import List, Optional

from core.logging_config import setup_logging

from .combiner import AudioCombiner
from .srt_generator import SRTGenerator
from .synthesizer import AudioSegmentSynthesizer

logger = setup_logging("tts.seedvc_server.batch_synthesis.service")


class BatchSynthesisService:
    """批量语音合成服务
    
    编排批量语音合成流程，包括：
    - 并行合成多个音频段
    - 组合音频段
    - 生成SRT字幕文件
    """
    
    def __init__(
        self,
        client,
        max_workers: int = 4,
        silence_duration_ms: int = 300,
        max_retries: int = 10,
        retry_delay: float = 0.3,
    ):
        """
        初始化服务
        
        Args:
            client: 语音合成客户端
            max_workers: 最大并发工作线程数
            silence_duration_ms: 段之间的静音时长（毫秒）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.client = client
        self.max_workers = max_workers
        self.synthesizer = AudioSegmentSynthesizer(
            client=client,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self.combiner = AudioCombiner(silence_duration_ms=silence_duration_ms)
        self.srt_generator = SRTGenerator(silence_duration_ms=silence_duration_ms)
    
    def synthesize_batch(
        self,
        text_list: List[str],
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
    ) -> Optional[List[tuple]]:
        """
        批量合成音频段
        
        Args:
            text_list: 文本列表
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
            (音频段, 文本, 索引) 元组列表，失败返回None
        """
        logger.info(f"开始批量合成 {len(text_list)} 个文本段")
        
        results_map = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(
                    self.synthesizer.synthesize_segment,
                    i,
                    text,
                    reference_audio_path,
                    voice,
                    volume,
                    speech_rate,
                    pitch_rate,
                    tts_type,
                    diffusion_steps,
                    length_adjust,
                    inference_cfg_rate,
                    temp_file_prefix,
                )
                for i, text in enumerate(text_list)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                segment_audio, text_content, original_index = future.result()
                
                if segment_audio:
                    results_map[original_index] = (segment_audio, text_content)
                else:
                    logger.error(
                        f"音频段 {original_index} 合成失败: '{text_content[:50]}...'"
                    )
                    # 清理临时文件
                    self._cleanup_temp_files(text_list, temp_file_prefix)
                    return None
        
        # 按原始顺序排列结果
        sorted_results = [
            results_map[i] for i in range(len(text_list))
            if i in results_map
        ]
        
        logger.info(f"批量合成完成，成功合成 {len(sorted_results)}/{len(text_list)} 个音频段")
        return sorted_results
    
    def _cleanup_temp_files(self, text_list: List[str], prefix: str) -> None:
        """清理临时文件"""
        for i in range(len(text_list)):
            temp_file = f"{prefix}_{i}.wav"
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, PermissionError) as e:
                    # 文件系统错误
                    logger.warning(f"[_cleanup_temp_files] 清理临时文件失败（文件系统错误） {temp_file}: {e}")
                except Exception as e:
                    # 其他异常
                    logger.warning(f"[_cleanup_temp_files] 清理临时文件失败 {temp_file}: {e}")
    
    def generate_audio_and_srt(
        self,
        text_list: List[str],
        reference_audio_path: str,
        voice: str,
        output_base_name: str,
        volume: int = 50,
        speech_rate: int = 0,
        pitch_rate: int = 0,
        tts_type: Optional[str] = 'edge',
        diffusion_steps: int = 50,
        length_adjust: float = 1.0,
        inference_cfg_rate: float = 0.7,
        temp_file_prefix: str = "temp_segment",
    ) -> Optional[str]:
        """
        生成完整音频和SRT文件
        
        Args:
            text_list: 文本列表
            reference_audio_path: 参考音频路径
            voice: 语音标识
            output_base_name: 输出文件基础名称（不含扩展名）
            volume: 音量
            speech_rate: 语速
            pitch_rate: 音调
            tts_type: TTS类型
            diffusion_steps: 扩散步数
            length_adjust: 长度调整
            inference_cfg_rate: 推理配置率
            temp_file_prefix: 临时文件前缀
            
        Returns:
            SRT文件路径，失败返回None
        """
        # 确保输出目录存在
        output_dir = os.path.dirname(output_base_name)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # 批量合成音频段
        segments = self.synthesize_batch(
            text_list=text_list,
            reference_audio_path=reference_audio_path,
            voice=voice,
            volume=volume,
            speech_rate=speech_rate,
            pitch_rate=pitch_rate,
            tts_type=tts_type,
            diffusion_steps=diffusion_steps,
            length_adjust=length_adjust,
            inference_cfg_rate=inference_cfg_rate,
            temp_file_prefix=temp_file_prefix,
        )
        
        if not segments:
            logger.error("批量合成失败，无法生成音频和SRT")
            return None
        
        # 组合音频
        combined_audio = self.combiner.combine_segments(segments)
        
        # 导出音频文件
        output_audio_path = f"{output_base_name}.wav"
        self.combiner.export_audio(combined_audio, output_audio_path)
        
        # 生成SRT文件
        srt_entries = self.srt_generator.generate_srt_entries(segments)
        output_srt_path = f"{output_base_name}.srt"
        self.srt_generator.write_srt_file(srt_entries, output_srt_path)
        
        logger.info("批量合成和SRT生成完成")
        return output_srt_path

