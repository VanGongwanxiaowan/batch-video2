"""
音频生成模块
负责TTS音频生成和字幕文件生成
"""
import os
import shutil
from typing import Optional

from clients.azure_tts_client import VoiceSynthesisClient
from clients.batch_synthesis import batch_synthesize_and_generate_srt
from utils.subtitle_formatter import process_srt_file
from utils.text_processor import split_string_by_punctuation

from core.logging_config import setup_logging
from core.utils.ffmpeg import run_ffmpeg, validate_path

from .path_config import PathConfig

logger = setup_logging("worker.utils.generation.audio_generator")


class AudioGenerator:
    """音频生成器"""
    
    def __init__(self) -> None:
        """初始化音频生成器"""
        self.path_config = PathConfig()
    
    def generate_audio_and_subtitle(
        self,
        content: str,
        language: str,
        platform: str,
        speech_speed: float,
        reference_audio_path: str,
        output_base_name: str,
        srtpath: str,
        seedvc_mp3_audio: str,
        is_horizontal: bool,
        job_id: int = 0,
    ) -> None:
        """
        生成音频和字幕文件
        
        Args:
            content: 文本内容
            language: 语言代码
            platform: TTS平台 (azure/edge)
            speech_speed: 语速
            reference_audio_path: 参考音频路径
            output_base_name: 输出文件基础名称
            srtpath: 字幕文件路径
            seedvc_mp3_audio: 输出MP3音频路径
            is_horizontal: 是否横向视频
            job_id: 任务ID
        """
        text_list = split_string_by_punctuation(content)
        square = self.path_config.is_square_language(language)
        output_audio_path = f"{output_base_name}.mp3"
        
        if not os.path.exists(output_audio_path) or not os.path.exists(srtpath):
            logger.info(
                f"[generate_audio_and_subtitle] 需要生成音频和字幕 "
                f"job_id={job_id}, platform={platform}"
            )
            
            if platform == "azure":
                self._generate_with_azure(
                    content, language, speech_speed,
                    seedvc_mp3_audio, srtpath, job_id
                )
            elif platform == "edge":
                self._generate_with_edge(
                    text_list, language, reference_audio_path,
                    output_base_name, srtpath, seedvc_mp3_audio,
                    square, is_horizontal, speech_speed, job_id
                )
            else:
                raise ValueError(f"Unsupported TTS platform: {platform}")
        else:
            logger.info(
                f"[generate_audio_and_subtitle] 音频和字幕文件已存在，跳过生成 "
                f"job_id={job_id}"
            )
    
    def _generate_with_azure(
        self,
        content: str,
        language: str,
        speech_speed: float,
        output_audio: str,
        srtpath: str,
        job_id: int,
    ) -> None:
        """使用Azure TTS生成音频"""
        logger.info(
            f"[generate_audio_and_subtitle] 使用Azure TTS生成音频 job_id={job_id}"
        )
        client = VoiceSynthesisClient()
        client.synthesize_voice(
            content,
            output_audio,
            srtpath,
            voice=language,
            speech_rate=speech_speed,
        )
    
    def _generate_with_edge(
        self,
        text_list: list,
        language: str,
        reference_audio_path: str,
        output_base_name: str,
        srtpath: str,
        seedvc_mp3_audio: str,
        square: bool,
        is_horizontal: bool,
        speech_speed: float,
        job_id: int,
    ) -> None:
        """使用Edge TTS生成音频"""
        logger.info(
            f"[generate_audio_and_subtitle] 使用Edge TTS批量生成音频和字幕 "
            f"job_id={job_id}"
        )
        
        # 批量生成音频和字幕
        srt_file_path = batch_synthesize_and_generate_srt(
            text_list=text_list,
            reference_audio_path=reference_audio_path,
            language=language,
            output_base_name=output_base_name,
            base_url="http://127.0.0.1:8007",
            sleep_ms=300,
            speech_rate=speech_speed,
            tts_type="edge",
            max_workers=16,
            job_id=job_id,
        )
        logger.info(
            f"[generate_audio_and_subtitle] Edge TTS批量生成完成 job_id={job_id}"
        )
        
        # 处理字幕文件
        srt_file_path = process_srt_file(srt_file_path, square, is_horizontal)
        logger.info(
            f"[generate_audio_and_subtitle] 字幕文件处理完成 job_id={job_id}"
        )
        
        if not srt_file_path:
            raise RuntimeError("Batch synthesis and SRT generation failed.")
        
        # 复制字幕文件
        shutil.copyfile(srt_file_path, srtpath)
        logger.info(
            f"[generate_audio_and_subtitle] 字幕文件复制完成 job_id={job_id}"
        )
        
        # 转换音频格式为MP3
        if not os.path.exists(seedvc_mp3_audio):
            logger.info(
                f"[generate_audio_and_subtitle] 转换音频格式为MP3 job_id={job_id}"
            )
            wav_input = validate_path(f"{output_base_name}.wav", must_exist=True)
            mp3_output = validate_path(seedvc_mp3_audio)
            run_ffmpeg([
                '-i', str(wav_input),
                '-y',
                '-acodec', 'libmp3lame',
                str(mp3_output)
            ])
            logger.info(
                f"[generate_audio_and_subtitle] 音频格式转换完成 job_id={job_id}"
            )


# 创建全局实例
audio_generator = AudioGenerator()

