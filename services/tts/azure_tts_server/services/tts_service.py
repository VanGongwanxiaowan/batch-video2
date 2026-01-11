"""Azure TTS 服务."""

import os
import re
import tempfile
from pathlib import Path
from typing import Optional

import azure.cognitiveservices.speech as speechsdk
import librosa
import numpy as np
import soundfile as sf
from opencc import OpenCC
from scipy.signal import resample

from config import get_azure_tts_config
from core.logging_config import setup_logging

logger = setup_logging("azure_tts_service", log_to_file=True)


class AzureTTSService:
    """Azure TTS 语音合成服务."""

    def __init__(
        self,
        speech_key: Optional[str] = None,
        service_region: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """
        初始化 Azure TTS 客户端.

        Args:
            speech_key: Azure Speech 服务订阅密钥
            service_region: Azure Speech 服务区域
            endpoint: 自定义端点 (可选)
        """
        config = get_azure_tts_config()
        self.speech_key = speech_key or config.AZURE_SPEECH_KEY
        self.service_region = service_region or config.AZURE_SERVICE_REGION
        self.endpoint = endpoint or config.AZURE_SPEECH_ENDPOINT

        # 初始化 Speech Config
        if self.endpoint:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                endpoint=self.endpoint,
            )
        else:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.service_region,
            )

        # 初始化繁体转简体转换器
        self._opencc_t2s = OpenCC("t2s")

        logger.info(
            f"Azure TTS 服务初始化完成 - Region: {self.service_region}, "
            f"Endpoint: {self.endpoint or 'default'}"
        )

    def synthesize_speech(
        self,
        text: str,
        audio_save_file: str,
        voice: str = "zh-CN-XiaoxiaoNeural",
        format: str = "wav",
        sample_rate: int = 16000,
        volume: int = 50,
        speech_rate: float = 1.0,
    ) -> bool:
        """
        合成语音并保存到文件.

        Args:
            text: 要合成的文本
            audio_save_file: 音频保存路径
            voice: 语音模型
            format: 输出音频格式 (目前仅支持 wav)
            sample_rate: 目标采样率
            volume: 音量调整 (0-100)
            speech_rate: 语速倍数

        Returns:
            成功返回 True, 失败返回 False
        """
        try:
            # 文本预处理
            processed_text = self._preprocess_text(text, voice)

            # 配置语音和输出格式
            self.speech_config.speech_synthesis_voice_name = voice

            if format.lower() == "wav":
                self.speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )
            else:
                logger.warning(
                    f"格式 '{format}' 不支持后处理, 使用 Riff16Khz16BitMonoPcm"
                )
                self.speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )

            # 构建 SSML 文本
            ssml_text = self._build_ssml(
                processed_text, voice, volume, speech_rate
            )

            # 创建临时文件
            temp_audio_file = None
            success = False

            try:
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp_file:
                    temp_audio_file = tmp_file.name

                # 执行语音合成
                audio_config = speechsdk.AudioConfig(
                    filename=temp_audio_file
                )
                speech_synthesizer = speechsdk.SpeechSynthesizer(
                    speech_config=self.speech_config,
                    audio_config=audio_config,
                )

                result = speech_synthesizer.speak_ssml_async(ssml_text).get()

                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    # 后处理音频
                    success = self._postprocess_audio(
                        temp_audio_file, audio_save_file, sample_rate
                    )
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation_details = result.cancellation_details
                    logger.error(
                        f"Azure TTS 合成取消: {cancellation_details.reason}"
                    )
                    if cancellation_details.reason == speechsdk.CancellationReason.Error:
                        if cancellation_details.error_details:
                            logger.error(
                                f"错误详情: {cancellation_details.error_details}"
                            )
                        logger.error(
                            "请确保订阅密钥和区域配置正确"
                        )
                    success = False
                else:
                    error_msg = f"Azure TTS 合成失败: {result.reason}"
                    logger.error(error_msg)
                    success = False

            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (OSError, IOError) as e:
                # 文件IO错误
                logger.error(f"[synthesize] 文件IO错误: {e}", exc_info=True)
                success = False
            except (RuntimeError, ValueError) as e:
                # 运行时错误或参数错误
                logger.error(f"[synthesize] 运行时错误: {e}", exc_info=True)
                success = False
            except Exception as e:
                # 其他异常（Azure TTS API错误等）
                logger.exception(f"[synthesize] 语音合成过程中发生错误: {e}")
                success = False
            finally:
                # 清理临时文件
                if temp_audio_file and os.path.exists(temp_audio_file):
                    try:
                        os.remove(temp_audio_file)
                    except OSError as e:
                        logger.warning(
                            f"无法删除临时文件 {temp_audio_file}: {e}"
                        )

            return success

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[synthesize] 合成语音时发生未预期的错误: {e}")
            return False

    def _preprocess_text(self, text: str, voice: str) -> str:
        """
        预处理文本.

        Args:
            text: 原始文本
            voice: 语音模型

        Returns:
            处理后的文本
        """
        # 繁体转简体（仅对中文语音模型）
        if "zh-" in voice.lower():
            try:
                text = self._opencc_t2s.convert(text)
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (ValueError, RuntimeError) as e:
                # 文本转换错误
                logger.warning(f"[_preprocess_text] 繁体转简体失败: {e}, 使用原文本")
            except Exception as e:
                # 其他未预期的异常
                logger.warning(f"[_preprocess_text] 繁体转简体失败: {e}, 使用原文本")

        # 去除首尾空白
        text = text.strip()

        # 移除零宽字符和特殊控制字符（保留常用标点）
        import re
        text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)  # 移除零宽字符

        return text

    def _build_ssml(
        self, text: str, voice: str, volume: int, speech_rate: float
    ) -> str:
        """
        构建 SSML 文本.

        Args:
            text: 文本内容
            voice: 语音模型
            volume: 音量
            speech_rate: 语速

        Returns:
            SSML 格式的文本
        """
        ssml_text = (
            f"<speak version='1.0' "
            f"xmlns='http://www.w3.org/2001/10/synthesis' "
            f"xml:lang='en-US'>"
            f"<voice name='{voice}'>"
        )

        prosody_attributes = []
        if speech_rate != 1.0:
            rate_percent = (speech_rate - 1.0) * 100
            prosody_attributes.append(f"rate='{rate_percent}%'")

        if volume != 50:  # 默认音量是 50
            volume_adjust = volume - 50
            prosody_attributes.append(f"volume='{volume_adjust}%'")

        if prosody_attributes:
            ssml_text += (
                f"<prosody {' '.join(prosody_attributes)}>"
                f"{text}</prosody>"
            )
        else:
            ssml_text += text

        ssml_text += "</voice></speak>"
        return ssml_text

    def _postprocess_audio(
        self,
        input_file: str,
        output_file: str,
        target_sample_rate: int,
    ) -> bool:
        """
        后处理音频: 修剪静音、重采样.

        Args:
            input_file: 输入音频文件
            output_file: 输出音频文件
            target_sample_rate: 目标采样率

        Returns:
            成功返回 True, 失败返回 False
        """
        try:
            # 确保输出目录存在
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 读取音频
            data, original_sample_rate = sf.read(input_file)

            # 确保数据是 numpy 数组
            if not isinstance(data, np.ndarray):
                data = np.array(data)

            # 处理立体声转单声道（如果需要）
            if len(data.shape) > 1 and data.shape[1] > 1:
                data = np.mean(data, axis=1)

            # 修剪静音（设置合适的阈值）
            trimmed_data, _ = librosa.effects.trim(
                data, top_db=20, frame_length=2048, hop_length=512
            )

            # 重采样
            if original_sample_rate != target_sample_rate:
                duration = len(trimmed_data) / original_sample_rate
                new_num_frames = int(duration * target_sample_rate)
                processed_data = resample(trimmed_data, new_num_frames)
                # 归一化到 [-1, 1] 范围
                max_val = np.abs(processed_data).max()
                if max_val > 0:
                    processed_data = processed_data / max_val
                processed_data = processed_data.astype(np.float32)
            else:
                processed_data = trimmed_data.astype(np.float32)
                # 归一化
                max_val = np.abs(processed_data).max()
                if max_val > 0:
                    processed_data = processed_data / max_val

            # 保存音频（确保输出目录存在）
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(output_file, processed_data, target_sample_rate, subtype='PCM_16')
            logger.debug(
                f"音频后处理完成: {output_file}, "
                f"采样率: {target_sample_rate}Hz"
            )
            return True

        except FileNotFoundError:
            logger.error(f"临时音频文件未找到: {input_file}")
            return False
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, IOError, PermissionError) as e:
            # 文件系统错误
            logger.error(f"[post_process_audio] 文件系统错误: {e}", exc_info=True)
            return False
        except (ValueError, RuntimeError) as e:
            # 音频处理错误（格式错误、处理失败等）
            logger.error(f"[post_process_audio] 音频处理错误: {e}", exc_info=True)
            return False
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[post_process_audio] 音频后处理时发生错误: {e}")
            return False

