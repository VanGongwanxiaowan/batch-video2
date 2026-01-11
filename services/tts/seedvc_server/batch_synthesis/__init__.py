"""批量语音合成模块

将批量语音合成功能拆分为独立的职责模块：
- AudioSegmentSynthesizer: 处理单个音频段的合成
- AudioCombiner: 组合多个音频段
- SRTGenerator: 生成SRT字幕文件
- BatchSynthesisService: 编排整个批量合成流程
"""

from .combiner import AudioCombiner
from .service import BatchSynthesisService
from .srt_generator import SRTGenerator, format_time
from .synthesizer import AudioSegmentSynthesizer

__all__ = [
    "AudioSegmentSynthesizer",
    "AudioCombiner",
    "SRTGenerator",
    "format_time",
    "BatchSynthesisService",
]

