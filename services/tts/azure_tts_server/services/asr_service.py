"""ASR (自动语音识别) 服务."""

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional

from funasr import AutoModel
from models import SentenceInfo

from config import get_azure_tts_config
from core.exceptions import FileNotFoundException, ServiceException
from core.logging_config import setup_logging

logger = setup_logging("asr_service", log_to_file=True)


class ASRService:
    """ASR 自动语音识别服务（线程安全）."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        vad_model_path: Optional[str] = None,
        punc_model_path: Optional[str] = None,
        spk_model_path: Optional[str] = None,
        device: Optional[str] = None,
    ):
        """
        初始化 ASR 服务.

        Args:
            model_path: ASR 模型路径
            vad_model_path: VAD 模型路径
            punc_model_path: 标点模型路径
            spk_model_path: 说话人模型路径
            device: 运行设备 (如 'cuda:0', 'cpu')
        """
        config = get_azure_tts_config()
        model_paths = config.asr_model_paths

        self.model_path = model_path or model_paths["model"]
        self.vad_model_path = vad_model_path or model_paths["vad_model"]
        self.punc_model_path = punc_model_path or model_paths["punc_model"]
        self.spk_model_path = spk_model_path or model_paths["spk_model"]
        self.device = device or config.ASR_DEVICE

        self._model: Optional[AutoModel] = None
        self._model_lock = threading.Lock()  # 模型加载锁

        logger.info(
            f"ASR 服务初始化 - Device: {self.device}, "
            f"Model: {self.model_path}"
        )

    @property
    def model(self) -> AutoModel:
        """获取 ASR 模型 (线程安全的懒加载)."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:  # 双重检查锁定
                    self._model = self._load_model()
        return self._model

    def _load_model(self) -> AutoModel:
        """
        加载 ASR 模型.

        Returns:
            加载的 ASR 模型
        """
        try:
            # 检查模型路径是否存在, 不存在则使用模型名称
            model = (
                self.model_path
                if os.path.exists(self.model_path)
                else "iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn"
            )
            vad_model = (
                self.vad_model_path
                if os.path.exists(self.vad_model_path)
                else "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch"
            )
            punc_model = (
                self.punc_model_path
                if os.path.exists(self.punc_model_path)
                else "iic/punc_ct-transformer_cn-en-common-vocab471067-large"
            )
            spk_model = (
                self.spk_model_path
                if os.path.exists(self.spk_model_path)
                else "iic/speech_campplus_sv_zh-cn_16k-common"
            )

            logger.info("开始加载 ASR 模型...")
            model_instance = AutoModel(
                model=model,
                vad_model=vad_model,
                punc_model=punc_model,
                spk_model=spk_model,
                device=self.device,
            )
            logger.info("ASR 模型加载完成")
            return model_instance

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (FileNotFoundError, OSError) as e:
            # 文件系统错误（模型文件不存在等）
            logger.error(f"[_load_model] 文件系统错误: {e}", exc_info=True)
            raise ServiceException(
                f"加载 ASR 模型失败: {str(e)}",
                service_name="asr"
            ) from e
        except (RuntimeError, ImportError) as e:
            # 运行时错误或导入错误
            logger.error(f"[_load_model] 运行时错误: {e}", exc_info=True)
            raise ServiceException(
                f"加载 ASR 模型失败: {str(e)}",
                service_name="asr"
            ) from e
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[_load_model] 加载 ASR 模型时发生错误: {e}")
            raise ServiceException(
                f"加载 ASR 模型失败: {str(e)}",
                service_name="asr"
            ) from e

    def transcribe_audio(self, audio_path: str) -> list[SentenceInfo]:
        """
        转录音频文件.

        Args:
            audio_path: 音频文件路径

        Returns:
            句子信息列表

        Raises:
            FileNotFoundException: 音频文件不存在
            ServiceException: 转录服务错误
        """
        try:
            # 验证文件存在
            if not os.path.exists(audio_path):
                raise FileNotFoundException(audio_path)

            # 验证文件不为空
            if os.path.getsize(audio_path) == 0:
                raise ServiceException(
                    f"音频文件为空: {audio_path}",
                    service_name="asr"
                )

            logger.debug(f"开始转录音频: {audio_path}")

            # 使用锁保证模型调用的线程安全
            with self._model_lock:
                result = self.model.generate(
                    input=audio_path,
                    sentence_timestamp=True,
                    return_raw_text=True,
                    is_final=True,
                )

            if not result or not isinstance(result, list) or len(result) == 0:
                logger.warning(f"音频转录结果为空: {audio_path}")
                return []

            # 安全地提取结果
            first_result = result[0] if isinstance(result[0], dict) else {}
            sentence_info = first_result.get("sentence_info", [])

            if not sentence_info:
                logger.warning(f"音频转录结果中无句子信息: {audio_path}")
                return []

            # 验证并转换句子信息
            asr_result = []
            for x in sentence_info:
                try:
                    sentence = SentenceInfo.model_validate(x)
                    asr_result.append(sentence)
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (ValueError, KeyError, AttributeError) as e:
                    # 数据验证错误
                    logger.warning(f"[transcribe_audio] 跳过无效的句子信息（数据格式错误）: {e}")
                except Exception as e:
                    # 其他异常
                    logger.warning(f"[transcribe_audio] 跳过无效的句子信息: {e}")

            logger.debug(
                f"音频转录完成: {audio_path}, "
                f"识别到 {len(asr_result)} 个句子"
            )
            return asr_result

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (FileNotFoundException, ServiceException):
            raise
        except Exception as e:
            # 其他异常（ASR处理错误等）
            logger.exception(f"[transcribe_audio] 转录音频时发生错误: {e}")
            raise ServiceException(
                f"转录音频失败: {str(e)}",
                service_name="asr"
            )


# 全局 ASR 服务实例 (线程安全的单例模式)
_asr_service: Optional[ASRService] = None
_asr_service_lock = threading.Lock()


def get_asr_service() -> ASRService:
    """获取全局 ASR 服务实例（线程安全）."""
    global _asr_service
    if _asr_service is None:
        with _asr_service_lock:
            if _asr_service is None:  # 双重检查锁定
                _asr_service = ASRService()
    return _asr_service

