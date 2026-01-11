"""TTS服务客户端实现

实现 ITTSService 接口，提供 TTS 语音合成功能。

性能优化：
- 使用共享 HTTP Session，避免频繁创建 TCP 连接
- 自动重试机制
"""
from pathlib import Path
from typing import Any, Dict, Optional

from core.exceptions import ServiceException
from core.interfaces.service_interfaces import ITTSService, TTSResult
from core.utils.exception_handler import handle_service_exceptions
from core.utils.http_session import get_http_session
from core.logging_config import setup_logging

from .base_client import BaseServiceClient

logger = setup_logging("core.clients.tts_client")


class TTSClient(BaseServiceClient, ITTSService):
    """TTS服务客户端

    实现 ITTSService 接口，提供同步和异步的语音合成功能。
    """

    def _build_synthesis_data(
        self,
        text: str,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        output_path: Optional[str] = None,
        subtitle_output_path: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        构建TTS合成请求数据（提取公共逻辑）

        Args:
            text: 要合成的文本
            voice: 音色名称
            volume: 音量(0-100)
            speech_rate: 语速
            output_path: 输出音频文件路径
            subtitle_output_path: 字幕输出路径
            **kwargs: 其他参数

        Returns:
            请求数据字典
        """
        data = {
            "text": text,
            "audio_text": text,
            "voice": voice or "zh-CN-XiaoqiuNeural",
            "volume": volume,
            "speech_rate": speech_rate,
        }
        if output_path:
            data["audio_output_path"] = output_path
        if subtitle_output_path:
            data["subtitle_output_path"] = subtitle_output_path
        data.update(kwargs)
        return data

    def synthesize(
        self,
        text: str,
        language: str,
        output_path: str,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        subtitle_output_path: Optional[str] = None,
        **kwargs,
    ) -> TTSResult:
        """同步合成语音 (实现 ITTSService 接口)

        Args:
            text: 要合成的文本
            language: 语言代码
            output_path: 输出音频文件路径
            voice: 音色名称
            volume: 音量(0-100)
            speech_rate: 语速
            subtitle_output_path: 字幕输出路径
            **kwargs: 其他参数

        Returns:
            TTSResult: 合成结果
        """
        import os

        try:
            # 使用内部的同步方法
            success = self.synthesize_sync(
                text=text,
                language=language,
                output_path=output_path,
                voice=voice,
                volume=volume,
                speech_rate=speech_rate,
                subtitle_output_path=subtitle_output_path,
                **kwargs
            )

            if success:
                # 计算音频时长
                duration = self._get_audio_duration(output_path)
                return TTSResult(
                    success=True,
                    audio_path=output_path,
                    srt_path=subtitle_output_path,
                    duration=duration
                )
            else:
                return TTSResult(
                    success=False,
                    error_message="TTS synthesis failed"
                )

        except Exception as e:
            logger.error(f"[TTSClient] TTS synthesis failed: {e}")
            return TTSResult(
                success=False,
                error_message=str(e)
            )

    @handle_service_exceptions("TTS", "synthesize")
    async def synthesize_async(
        self,
        text: str,
        language: str,
        output_path: str,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        **kwargs,
    ) -> TTSResult:
        """异步合成语音 (实现 ITTSService 接口)

        Args:
            text: 要合成的文本
            language: 语言代码
            output_path: 输出音频文件路径
            voice: 音色名称
            volume: 音量(0-100)
            speech_rate: 语速
            **kwargs: 其他参数

        Returns:
            TTSResult: 合成结果
        """
        import os

        subtitle_output_path = kwargs.pop("subtitle_output_path", None)

        endpoint = "/asr_service"
        data = self._build_synthesis_data(
            text=text,
            voice=voice,
            volume=volume,
            speech_rate=speech_rate,
            output_path=output_path,
            subtitle_output_path=subtitle_output_path,
            **kwargs,
        )

        # 使用POST请求发送数据
        response = await self.client.post(endpoint, data=data, timeout=1800)

        # 验证文件是否生成
        if not os.path.exists(output_path):
            return TTSResult(
                success=False,
                error_message="Audio file not generated"
            )

        # 计算时长
        duration = self._get_audio_duration(output_path)

        return TTSResult(
            success=True,
            audio_path=output_path,
            srt_path=subtitle_output_path,
            duration=duration
        )

    def synthesize_sync(
        self,
        text: str,
        language: str,
        output_path: Optional[str] = None,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        subtitle_output_path: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        同步调用TTS服务合成语音 (向后兼容方法)

        使用共享 HTTP Session，自动复用 TCP 连接。

        Args:
            text: 要合成的文本
            language: 语言代码
            output_path: 输出音频文件路径
            voice: 音色名称
            volume: 音量(0-100)
            speech_rate: 语速
            subtitle_output_path: 字幕输出路径
            **kwargs: 其他参数

        Returns:
            是否成功

        Raises:
            ServiceException: TTS合成失败
        """
        from core.logging_config import setup_logging
        logger = setup_logging("core.clients.tts_client")

        endpoint = f"{self.base_url}/asr_service"
        data = self._build_synthesis_data(
            text=text,
            voice=voice,
            volume=volume,
            speech_rate=speech_rate,
            output_path=output_path,
            subtitle_output_path=subtitle_output_path,
            **kwargs,
        )

        # 使用共享 Session（自动连接池 + 重试）
        session = get_http_session()

        for attempt in range(2):  # Session 已配置自动重试，减少手动重试
            try:
                response = session.post(endpoint, data=data, timeout=1800)
                response.raise_for_status()
                return True
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception as e:
                logger.warning(f"[synthesize_sync] TTS synthesis attempt {attempt + 1} failed: {e}")
                if attempt == 1:  # 最后一次尝试
                    raise ServiceException(
                        f"TTS synthesis failed after 2 attempts: {str(e)}",
                        "TTS"
                    )
        return False

    def _get_audio_duration(self, audio_path: str) -> float:
        """获取音频时长

        Args:
            audio_path: 音频文件路径

        Returns:
            float: 音频时长（秒）
        """
        try:
            import librosa
            duration = librosa.get_duration(filename=audio_path)
            return duration
        except ImportError:
            logger.warning(f"[TTSClient] librosa not installed, cannot get audio duration")
            return 0.0
        except Exception as e:
            logger.error(f"[TTSClient] Failed to get audio duration: {e}")
            return 0.0

