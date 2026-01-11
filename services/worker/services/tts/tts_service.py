"""TTS服务"""
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from clients.azure_tts_client import VoiceSynthesisClient
from clients.batch_synthesis import batch_synthesize_and_generate_srt
from utils.file_manager import FileManager

from core.config.constants import TTSConfig, WorkerConfig
from core.exceptions import FFmpegError, ServiceException
from core.logging_config import setup_logging
from core.utils.exception_handler import handle_service_method_exceptions
from services.base import BaseService

logger = setup_logging("worker.tts")


class TTSService(BaseService):
    """TTS服务，负责音频生成和字幕生成"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config, logger)
        self.file_manager = FileManager()
    
    @handle_service_method_exceptions("TTS", "synthesize_azure")
    async def synthesize_azure(
        self,
        text: str,
        output_audio_path: str,
        output_srt_path: str,
        language: str,
        speech_rate: float = 1.0,
    ) -> Dict[str, Any]:
        """
        使用Azure TTS生成音频和字幕
        
        Args:
            text: 要合成的文本
            output_audio_path: 输出音频文件路径
            output_srt_path: 输出字幕文件路径
            language: 语言代码
            speech_rate: 语音速度
            
        Returns:
            包含音频路径和字幕路径的字典
        """
        client = VoiceSynthesisClient()
        client.synthesize_voice(
            text,
            output_audio_path,
            output_srt_path,
            voice=language,
            speech_rate=speech_rate,
        )
        return {
            "success": True,
            "audio_path": output_audio_path,
            "srt_path": output_srt_path
        }
    
    @handle_service_method_exceptions("TTS", "synthesize_edge")
    async def synthesize_edge(
        self,
        text: str,
        output_base_name: str,
        output_srt_path: str,
        language: str,
        reference_audio_path: Optional[str] = None,
        speech_rate: float = 1.0,
        job_id: int = 0,
    ) -> Dict[str, Any]:
        """
        使用Edge TTS批量生成音频和字幕
        
        Args:
            text: 要合成的文本
            output_base_name: 输出文件基础名称（不含扩展名）
            output_srt_path: 输出字幕文件路径
            language: 语言代码
            reference_audio_path: 参考音频路径（可选）
            speech_rate: 语音速度
            job_id: 任务ID
            
        Returns:
            包含音频路径和字幕路径的字典
        """
        # 文本分段
        text_list = self.file_manager.split_string_by_punctuation(text)
        
        # 批量生成
        srt_file_path = batch_synthesize_and_generate_srt(
            text_list=text_list,
            reference_audio_path=reference_audio_path,
            language=language,
            output_base_name=output_base_name,
            base_url=TTSConfig.DEFAULT_SEEDVC_BASE_URL,
            sleep_ms=TTSConfig.DEFAULT_SLEEP_MS,
            speech_rate=speech_rate,
            tts_type="edge",
            max_workers=WorkerConfig.DEFAULT_MAX_WORKERS * 4,  # 使用配置常量
            job_id=job_id,
        )
        
        if not srt_file_path:
            return {
                "success": False,
                "error": "批量合成和SRT生成失败"
            }
        
        # 复制字幕文件
        shutil.copyfile(srt_file_path, output_srt_path)
        
        # 转换音频格式为MP3
        wav_path = f"{output_base_name}.wav"
        mp3_path = f"{output_base_name}.mp3"
        if os.path.exists(wav_path) and not os.path.exists(mp3_path):
            from core.utils import ffmpeg_utils
            try:
                ffmpeg_utils.convert_audio_format(wav_path, mp3_path, 'libmp3lame')
            except (OSError, PermissionError, FileNotFoundError) as e:
                # 文件系统错误，记录但不影响主流程
                logger.warning(f"[synthesize_edge] 音频格式转换失败（文件系统错误），继续使用wav文件: {e}")
            except FFmpegError as e:
                # FFmpeg处理错误，记录但不影响主流程
                logger.warning(f"[synthesize_edge] 音频格式转换失败（FFmpeg错误），继续使用wav文件: {e}")
            except Exception as e:
                # 其他转换错误，记录但不影响主流程
                logger.warning(f"[synthesize_edge] 音频格式转换失败，继续使用wav文件: {e}")
        
        return {
            "success": True,
            "audio_path": mp3_path if os.path.exists(mp3_path) else wav_path,
            "srt_path": output_srt_path
        }
    
    async def synthesize(
        self,
        text: str,
        output_audio_path: str,
        output_srt_path: str,
        language: str,
        platform: str = "edge",
        reference_audio_path: Optional[str] = None,
        speech_rate: float = 1.0,
        job_id: int = 0,
    ) -> Dict[str, Any]:
        """
        合成语音（根据平台选择不同的TTS服务）
        
        Args:
            text: 要合成的文本
            output_audio_path: 输出音频文件路径
            output_srt_path: 输出字幕文件路径
            language: 语言代码
            platform: TTS平台（"azure" 或 "edge"）
            reference_audio_path: 参考音频路径（可选，仅用于edge）
            speech_rate: 语音速度
            job_id: 任务ID
            
        Returns:
            包含音频路径和字幕路径的字典
        """
        if platform == "azure":
            return await self.synthesize_azure(
                text, output_audio_path, output_srt_path, language, speech_rate
            )
        elif platform == "edge":
            output_base_name = output_audio_path.replace(".mp3", "")
            return await self.synthesize_edge(
                text, output_base_name, output_srt_path, language,
                reference_audio_path, speech_rate, job_id
            )
        else:
            return {
                "success": False,
                "error": f"不支持的TTS平台: {platform}"
            }
    
    async def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理TTS请求
        
        Args:
            data: 包含TTS参数的字典
            
        Returns:
            处理结果字典
        """
        return await self.synthesize(
            text=data.get("text", ""),
            output_audio_path=data.get("output_audio_path", ""),
            output_srt_path=data.get("output_srt_path", ""),
            language=data.get("language", ""),
            platform=data.get("platform", "edge"),
            reference_audio_path=data.get("reference_audio_path"),
            speech_rate=data.get("speech_rate", 1.0),
            job_id=data.get("job_id", 0),
        )

