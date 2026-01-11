"""API 路由定义."""

import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Form, HTTPException
from models import TTSResponse
from utils import AudioProcessor, TextSplitter

from config import get_azure_tts_config
from core.exceptions import (
    BatchShortException,
    ConfigurationException,
    ServiceException,
    ValidationException,
)
from core.logging_config import setup_logging
from services import ASRService, AzureTTSService, SubtitleService
from services.asr_service import get_asr_service

logger = setup_logging("api_routes", log_to_file=True)

router = APIRouter(prefix="/api/v1", tags=["TTS"])

# 全局服务实例（使用线程锁保证线程安全）
_config = get_azure_tts_config()
_tts_service: Optional[AzureTTSService] = None
_subtitle_service: Optional[SubtitleService] = None
_text_splitter: Optional[TextSplitter] = None
_service_lock = threading.Lock()


def get_tts_service() -> AzureTTSService:
    """获取 TTS 服务实例（线程安全的单例模式）."""
    global _tts_service
    if _tts_service is None:
        with _service_lock:
            if _tts_service is None:  # 双重检查锁定
                _tts_service = AzureTTSService()
    return _tts_service


def get_subtitle_service() -> SubtitleService:
    """获取字幕服务实例（线程安全的单例模式）."""
    global _subtitle_service
    if _subtitle_service is None:
        with _service_lock:
            if _subtitle_service is None:  # 双重检查锁定
                _subtitle_service = SubtitleService()
    return _subtitle_service


def get_text_splitter() -> TextSplitter:
    """获取文本分割器实例（线程安全的单例模式）."""
    global _text_splitter
    if _text_splitter is None:
        with _service_lock:
            if _text_splitter is None:  # 双重检查锁定
                _text_splitter = TextSplitter()
    return _text_splitter


@router.post("/tts/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    audio_output_path: str = Form(..., description="音频输出路径"),
    audio_text: str = Form(..., description="要合成的文本", min_length=1),
    subtitle_output_path: Optional[str] = Form(
        None, description="字幕输出路径(可选)"
    ),
    voice: str = Form(
        default="zh-CN-XiaoqiuNeural", description="语音模型"
    ),
    sample_rate: int = Form(default=16000, description="采样率", ge=8000, le=48000),
    volume: int = Form(default=50, description="音量 (0-100)", ge=0, le=100),
    speech_rate: float = Form(default=1.0, description="语速倍数", gt=0, le=3.0),
) -> TTSResponse:
    """
    TTS 语音合成服务接口.

    该接口将文本转换为语音,并可选择生成字幕文件.

    Args:
        audio_output_path: 音频输出路径
        audio_text: 要合成的文本
        subtitle_output_path: 字幕输出路径(可选)
        voice: 语音模型
        sample_rate: 采样率
        volume: 音量 (0-100)
        speech_rate: 语速倍数

    Returns:
        TTSResponse: 包含处理结果的响应

    Raises:
        ConfigurationException: 配置错误
        ValidationException: 输入验证失败
        ServiceException: 服务处理失败
    """
    temp_wav_files = []
    filelist_path = None
    final_wav_file = None
    temp_mp3_file = None

    try:
        # 输入验证
        if not audio_text or not audio_text.strip():
            raise ValidationException(
                "要合成的文本不能为空",
                field="audio_text"
            )

        if not audio_output_path or not audio_output_path.strip():
            raise ValidationException(
                "音频输出路径不能为空",
                field="audio_output_path"
            )

        # 验证配置
        if not _config.AZURE_SPEECH_KEY:
            raise ConfigurationException(
                "Azure Speech Key 未配置",
                config_key="AZURE_SPEECH_KEY"
            )

        tts_service = get_tts_service()
        text_splitter = get_text_splitter()
        audio_processor = AudioProcessor()

        # 分割文本
        logger.info(f"开始处理 TTS 请求 - 文本长度: {len(audio_text)}")
        text_chunks = text_splitter.split_text(audio_text)
        logger.info(f"文本分割完成 - 分块数: {len(text_chunks)}")

        # 生成每个文本块的音频
        for i, chunk_text in enumerate(text_chunks):
            logger.debug(f"正在合成第 {i+1}/{len(text_chunks)} 个文本块...")
            temp_wav_chunk_file = tempfile.NamedTemporaryFile(
                suffix=f"_{i}.wav", delete=False
            ).name

            # 重试机制 (最多3次)
            success = False
            for attempt in range(3):
                try:
                    success = tts_service.synthesize_speech(
                        chunk_text,
                        temp_wav_chunk_file,
                        voice=voice,
                        sample_rate=sample_rate,
                        volume=volume,
                        speech_rate=speech_rate,
                    )
                    if success:
                        temp_wav_files.append(temp_wav_chunk_file)
                        break
                    else:
                        logger.warning(
                            f"第 {attempt+1} 次合成失败, 重试中..."
                        )
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (ServiceException, RuntimeError) as e:
                    # TTS服务错误或运行时错误
                    logger.warning(
                        f"第 {attempt+1} 次合成异常: {e}, 重试中..."
                    )
                except Exception as e:
                    # 其他未预期的异常
                    logger.warning(
                        f"第 {attempt+1} 次合成异常: {e}, 重试中..."
                    )

            if not success:
                logger.error(f"文本块 {i+1} 合成失败, 已重试3次")
                raise ServiceException(
                    f"文本块 {i+1} 合成失败",
                    service_name="azure_tts"
                )

        # 合并所有 WAV 文件
        logger.info(f"开始合并 {len(temp_wav_files)} 个音频文件...")
        final_wav_file = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ).name

        audio_processor.merge_wav_files(temp_wav_files, final_wav_file)

        # 转换为 MP3 (如果需要)
        output_path = Path(audio_output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.suffix.lower() == ".mp3":
            # 先转换为 MP3
            temp_mp3_file = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ).name
            try:
                audio_processor.convert_wav_to_mp3(final_wav_file, temp_mp3_file)
                # 移动到最终位置（使用原子操作）
                if os.path.exists(audio_output_path):
                    os.remove(audio_output_path)
                os.rename(temp_mp3_file, audio_output_path)
                temp_mp3_file = None  # 标记为已处理，避免删除
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (OSError, PermissionError, FileNotFoundError) as e:
                # 文件系统错误
                logger.error(f"[synthesize_voice] 文件系统错误: {e}", exc_info=True)
                raise ServiceException(
                    f"音频格式转换失败: {str(e)}",
                    service_name="audio_processor"
                )
            except (ValueError, RuntimeError) as e:
                # 音频处理错误（格式错误、处理失败等）
                logger.error(f"[synthesize_voice] 音频处理错误: {e}", exc_info=True)
                raise ServiceException(
                    f"音频格式转换失败: {str(e)}",
                    service_name="audio_processor"
                )
            except Exception as e:
                # 其他未预期的异常
                logger.error(f"[synthesize_voice] 转换 MP3 失败: {e}", exc_info=True)
                raise ServiceException(
                    f"音频格式转换失败: {str(e)}",
                    service_name="audio_processor"
                )
        else:
            # 直接移动 WAV 文件（使用原子操作）
            if os.path.exists(audio_output_path):
                os.remove(audio_output_path)
            os.rename(final_wav_file, audio_output_path)
            final_wav_file = None  # 标记为已处理，避免删除

        logger.info(f"音频文件生成成功: {audio_output_path}")

        # 生成字幕 (如果需要)
        subtitle_file = None
        if subtitle_output_path:
            try:
                logger.info("开始生成字幕...")
                asr_service = get_asr_service()
                subtitle_service = get_subtitle_service()

                # 转录音频
                sentences = asr_service.transcribe_audio(audio_output_path)

                # 生成字幕文件
                subtitle_file = subtitle_service.save_srt(
                    sentences, subtitle_output_path, audio_text
                )

                logger.info(f"字幕文件生成成功: {subtitle_file}")

            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (ServiceException, FileException) as e:
                # 字幕服务错误或文件操作错误
                logger.exception(f"[synthesize_voice] 生成字幕时发生错误: {e}")
                # 字幕生成失败不影响主流程, 返回警告
                return TTSResponse(
                    success=True,
                    message=f"音频生成成功, 但字幕生成失败: {str(e)}",
                    audio_file=audio_output_path,
                    subtitle_file=None,
                )
            except Exception as e:
                # 其他未预期的异常
                logger.exception(f"[synthesize_voice] 生成字幕时发生错误: {e}")
                # 字幕生成失败不影响主流程, 返回警告
                return TTSResponse(
                    success=True,
                    message=f"音频生成成功, 但字幕生成失败: {str(e)}",
                    audio_file=audio_output_path,
                    subtitle_file=None,
                )

        return TTSResponse(
            success=True,
            message="TTS 服务处理完成",
            audio_file=audio_output_path,
            subtitle_file=subtitle_file,
        )

    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (HTTPException, BatchShortException):
        raise
    except Exception as e:
        # 其他未预期的异常
        logger.exception(f"[synthesize_voice] 处理 TTS 请求时发生未预期的错误: {e}")
        raise ServiceException(
            f"TTS 服务处理失败: {str(e)}",
            service_name="azure_tts"
        )
    finally:
        # 清理临时文件
        cleanup_files = []
        cleanup_files.extend(temp_wav_files)
        if filelist_path and os.path.exists(filelist_path):
            cleanup_files.append(filelist_path)
        if final_wav_file and os.path.exists(final_wav_file):
            cleanup_files.append(final_wav_file)
        if temp_mp3_file and os.path.exists(temp_mp3_file):
            cleanup_files.append(temp_mp3_file)

        if cleanup_files:
            AudioProcessor.cleanup_files(cleanup_files)
            logger.debug(f"已清理 {len(cleanup_files)} 个临时文件")


@router.post("/asr_service", response_model=TTSResponse, deprecated=True)
async def asr_service_deprecated(
    audio_output_path: str = Form(..., description="音频输出路径"),
    audio_text: str = Form(..., description="要合成的文本", min_length=1),
    subtitle_output_path: Optional[str] = Form(
        None, description="字幕输出路径(可选)"
    ),
    voice: str = Form(
        default="zh-CN-XiaoqiuNeural", description="语音模型"
    ),
    sample_rate: int = Form(default=16000, description="采样率", ge=8000, le=48000),
    volume: int = Form(default=50, description="音量 (0-100)", ge=0, le=100),
    speech_rate: float = Form(default=1.0, description="语速倍数", gt=0, le=3.0),
) -> TTSResponse:
    """
    已弃用的TTS服务接口（保留用于向后兼容）.

    请使用 /tts/synthesize 接口替代此接口.
    """
    # 直接调用新的接口
    return await synthesize_speech(
        audio_output_path=audio_output_path,
        audio_text=audio_text,
        subtitle_output_path=subtitle_output_path,
        voice=voice,
        sample_rate=sample_rate,
        volume=volume,
        speech_rate=speech_rate,
    )


@router.get("/health")
async def health_check() -> dict:
    """
    健康检查接口.

    Returns:
        包含服务状态的字典
    """
    return {
        "status": "healthy",
        "service": "azure_tts_server",
        "version": _config.APP_VERSION,
    }

