"""批量语音合成模块（向后兼容接口）

此模块提供了向后兼容的函数接口，内部使用重构后的 BatchSynthesisService。
新代码应直接使用 batch_synthesis.service.BatchSynthesisService。
"""

import sys
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from batch_synthesis.service import BatchSynthesisService
from client import VoiceSynthesisClient, edge_lang_voice_map

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("tts.seedvc_server.batch_synthesis", log_to_file=False)


def batch_synthesize_and_generate_srt(
    text_list: List[str],
    reference_audio_path: str,
    language: str,
    output_base_name: str,
    base_url: str = "http://10.147.20.56:8000",
    sleep_ms: int = 300,
    volume: int = 50,
    speech_rate: int = 0,
    pitch_rate: int = 0,
    tts_type: Optional[str] = 'edge',
    diffusion_steps: int = 50,
    length_adjust: float = 1.0,
    inference_cfg_rate: float = 0.7,
    max_workers: int = 4
) -> Optional[str]:
    """
    批量合成文本列表，生成音频和SRT文件（向后兼容接口）
    
    Args:
        text_list: 要合成的文本列表
        reference_audio_path: 参考音频文件路径（用于音色克隆）
        language: 语言标识（如 '英语', '中文'）
        output_base_name: 输出文件基础名称（不含扩展名）
        base_url: 语音合成API的基础URL
        sleep_ms: 音频段之间的静音时长（毫秒）
        volume: 音量级别 (0-100)
        speech_rate: 语速调整
        pitch_rate: 音调调整
        tts_type: TTS引擎类型 ('edge' 或 'aly')
        diffusion_steps: 'aly' TTS的扩散步数
        length_adjust: 'aly' TTS的长度调整
        inference_cfg_rate: 推理配置率
        max_workers: 最大并发工作线程数
        
    Returns:
        生成的SRT文件路径，失败返回None
        
    Note:
        此函数为向后兼容接口，新代码应使用 BatchSynthesisService 类。
    """
    client = VoiceSynthesisClient(base_url)
    
    voice = edge_lang_voice_map.get(language)
    if not voice:
        logger.error(f"Error: Language '{language}' not found in voice map.")
        return None
    
    service = BatchSynthesisService(
        client=client,
        max_workers=max_workers,
        silence_duration_ms=sleep_ms,
    )
    
    return service.generate_audio_and_srt(
        text_list=text_list,
        reference_audio_path=reference_audio_path,
        voice=voice,
        output_base_name=output_base_name,
        volume=volume,
        speech_rate=speech_rate,
        pitch_rate=pitch_rate,
        tts_type=tts_type,
        diffusion_steps=diffusion_steps,
        length_adjust=length_adjust,
        inference_cfg_rate=inference_cfg_rate,
    )
