# -*- coding: utf-8 -*-
"""
EdgeTTS 语音合成服务封装
提供基于 Microsoft Edge TTS 的语音合成功能
"""
import asyncio
import functools
import os
import sys
import tempfile
import threading
import time
from typing import Optional

import edge_tts
import librosa
import nest_asyncio
import numpy as np
import soundfile as sf
from scipy.signal import resample

from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.edge_tts")

# 允许嵌套事件循环
nest_asyncio.apply()


def timeout_thread(seconds: int):
    """
    线程超时装饰器
    
    Args:
        seconds: 超时时间（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result_container = []
            exception_container = []

            def target():
                try:
                    result = func(*args, **kwargs)
                    result_container.append(result)
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except Exception as e:
                    # 其他异常
                    exception_container.append(e)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)

            if thread.is_alive():
                raise TimeoutError(
                    f"Function '{func.__name__}' timed out after {seconds} seconds."
                )
            
            if exception_container:
                raise exception_container[0]
            
            return result_container[0] if result_container else None

        return wrapper
    return decorator


def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    Args:
        coro: 异步协程
        
    Returns:
        协程的执行结果
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


class EdgeTTS:
    """EdgeTTS 语音合成客户端"""
    
    def __init__(self, proxy: Optional[str] = None):
        """
        初始化 EdgeTTS 客户端
        
        Args:
            proxy: 可选的代理设置 (例如: "http://127.0.0.1:10809")
        """
        self.proxy = proxy
        logger.info(f"EdgeTTS 客户端初始化完成，proxy={proxy}")

    def synthesize_speech(
        self,
        text: str,
        audio_save_file: str,
        voice: str = "en-US-AriaNeural",
        format: str = "wav",
        sample_rate: int = 16000,
        volume: int = 50,
        speech_rate: float = 1.0,
        pitch_rate: int = 0,
        method: str = "GET"
    ) -> bool:
        """
        合成语音并保存到文件
        
        Args:
            text: 要合成的文本
            audio_save_file: 保存音频文件的路径
            voice: 语音模型名称
            format: 音频格式
            sample_rate: 目标采样率
            volume: 音量 (0-100)
            speech_rate: 语速倍数
            pitch_rate: 音调调整
            method: HTTP 方法（未使用，保留兼容性）
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        logger.info(f"开始合成语音: text='{text[:min(len(text), 50)]}...', voice={voice}")
        
        # 转换语速格式
        rate_str = self._convert_rate_to_edge_format(speech_rate)
        
        temp_audio_file = None
        success = False

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_audio_file = tmp_file.name

            # 执行异步合成
            logger.debug(f"开始异步合成，临时文件: {temp_audio_file}")
            stream_success = run_async(
                self._perform_synthesis_async(text, temp_audio_file, voice, rate_str)
            )

            if stream_success:
                logger.debug(f"音频流保存成功: {temp_audio_file}")
                # 后处理：读取、去除静音、重采样、保存
                try:
                    data, original_sample_rate = sf.read(temp_audio_file)
                    logger.debug(f"原始采样率: {original_sample_rate} Hz")

                    # 去除首尾静音
                    logger.debug("去除静音...")
                    trimmed_data, index = librosa.effects.trim(data)
                    logger.debug(f"从 {len(data)} 帧修剪到 {len(trimmed_data)} 帧")
                    
                    processed_data = trimmed_data

                    # 重采样（如果需要）
                    if original_sample_rate != sample_rate:
                        logger.debug(f"重采样: {original_sample_rate} Hz -> {sample_rate} Hz")
                        duration = len(trimmed_data) / original_sample_rate
                        new_num_frames = int(duration * sample_rate)
                        processed_data = resample(trimmed_data, new_num_frames)
                        processed_data = processed_data.astype(np.float32)
                    else:
                        logger.debug("无需重采样")
                        processed_data = trimmed_data.astype(np.float32)

                    # 保存最终文件
                    sf.write(audio_save_file, processed_data, sample_rate)
                    logger.info(f"处理后的音频已保存: {audio_save_file}")
                    success = True

                except FileNotFoundError:
                    logger.error(f"临时音频文件未找到: {temp_audio_file}")
                    success = False
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (OSError, IOError, ValueError) as e:
                    # 文件IO错误或音频处理错误
                    logger.error(f"[synthesize_speech] 文件IO或音频处理错误: {e}", exc_info=True)
                    success = False
                except Exception as e:
                    # 其他异常
                    logger.error(f"[synthesize_speech] 音频处理失败: {e}", exc_info=True)
                    success = False
            else:
                logger.error(f"音频流合成失败: text='{text[:min(len(text), 50)]}...'")
                success = False

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（EdgeTTS合成错误等）
            logger.error(f"[synthesize_speech] 合成过程异常: {e}", exc_info=True)
            success = False

        finally:
            # 清理临时文件
            if temp_audio_file and os.path.exists(temp_audio_file):
                try:
                    os.remove(temp_audio_file)
                    logger.debug(f"已清理临时文件: {temp_audio_file}")
                except OSError as e:
                    logger.warning(f"无法删除临时文件 {temp_audio_file}: {e}")

        return success

    def _convert_rate_to_edge_format(self, rate: float) -> str:
        """
        将浮点语速转换为 Edge TTS 字符串格式
        
        Args:
            rate: 语速倍数
            
        Returns:
            Edge TTS 格式的语速字符串
        """
        if isinstance(rate, (int, float)):
            if rate <= 0:
                logger.warning(f"语速倍数 {rate} 不是正数，使用正常语速")
                return "+0%"
            else:
                percentage_change = (rate - 1.0) * 100
                rounded_percentage = round(percentage_change)
                rate_str = f"{'+' if rounded_percentage >= 0 else ''}{rounded_percentage}%"
                logger.debug(f"转换语速 {rate} 到 Edge TTS 格式: {rate_str}")
                return rate_str
        elif isinstance(rate, str):
            return rate
        else:
            logger.warning(f"语速 {rate} 不是浮点数或字符串，使用默认 '+0%'")
            return "+0%"

    async def _perform_synthesis_async(
        self,
        text: str,
        audio_save_file: str,
        voice: str,
        rate_str: str
    ) -> bool:
        """
        异步执行语音合成
        
        Args:
            text: 要合成的文本
            audio_save_file: 保存音频文件的路径
            voice: 语音模型名称
            rate_str: Edge TTS 格式的语速字符串
            
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(f"尝试合成 (尝试 {attempt + 1}/{max_retries})")
                
                with open(audio_save_file, "wb") as f:
                    @timeout_thread(25)
                    async def getcomm(text_split, p_voice, rate_str, proxy, f):
                        communicate = edge_tts.Communicate(
                            text_split, p_voice, rate=rate_str, proxy=proxy
                        )
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                f.write(chunk["data"])
                    
                    await getcomm(text, voice, rate_str, self.proxy, f)
                
                logger.debug("音频流合成成功")
                return True

            except TimeoutError as e:
                logger.warning(f"合成超时 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    logger.error(f"合成超时，已重试 {max_retries} 次")
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（EdgeTTS合成错误等）
                logger.warning(f"[_perform_synthesis_async] 合成异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    logger.error(f"[_perform_synthesis_async] 合成失败，已重试 {max_retries} 次: {e}")
        
        return False
