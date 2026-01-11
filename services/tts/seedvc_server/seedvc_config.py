"""
SeedVC语音克隆配置模块
定义语音克隆所需的配置数据类和常量
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import torch

# 采样率常量
SAMPLE_RATE_16K = 16000
SAMPLE_RATE_22K = 22050
SAMPLE_RATE_44K = 44100

# 时间窗口常量
LONG_AUDIO_CHUNK_DURATION = 30  # 秒
LONG_AUDIO_OVERLAP_DURATION = 5  # 秒
MAX_REF_AUDIO_DURATION = 25  # 秒

# 音频处理常量
HOP_LENGTH_NO_F0 = 256
HOP_LENGTH_WITH_F0 = 512
OVERLAP_FRAME_LEN = 16

# F0处理常量
F0_THRESHOLD = 0.03
F0_EPSILON = 1e-5


@dataclass
class SeedVCConfig:
    """SeedVC语音克隆配置数据类
    
    封装 seedvc_clone 函数的所有参数，提供类型安全和默认值支持。
    遵循单一职责原则，将配置参数与业务逻辑分离。
    
    Attributes:
        source: 源音频文件路径
        target: 目标参考音频文件路径
        output: 输出文件路径，默认'sed_test.wav'
        diffusion_steps: 扩散步数，默认30
        length_adjust: 长度调整因子，默认1.0
        inference_cfg_rate: 推理配置率，默认0.7
        f0_condition: 是否使用F0条件，默认False
        auto_f0_adjust: 是否自动调整F0，默认False
        pitch_shift: 音调偏移（半音），默认0
    """
    source: str
    target: str
    output: str = 'sed_test.wav'
    diffusion_steps: int = 30
    length_adjust: float = 1.0
    inference_cfg_rate: float = 0.7
    f0_condition: bool = False
    auto_f0_adjust: bool = False
    pitch_shift: int = 0
    
    def validate(self) -> None:
        """验证配置参数
        
        Raises:
            ValueError: 如果参数无效
        """
        if not self.source:
            raise ValueError("源音频文件路径不能为空")
        if not self.target:
            raise ValueError("目标音频文件路径不能为空")
        if self.diffusion_steps < 1:
            raise ValueError("扩散步数必须大于0")
        if self.length_adjust <= 0:
            raise ValueError("长度调整因子必须大于0")
        if not 0 <= self.inference_cfg_rate <= 1:
            raise ValueError("推理配置率必须在0-1之间")


@dataclass
class SeedVCModelConfig:
    """SeedVC模型配置数据类
    
    封装所有模型相关的参数。
    
    Attributes:
        model: DiT模型
        semantic_fn: 语义特征提取函数，接受torch.Tensor，返回torch.Tensor
        f0_fn: F0提取函数（可选），接受numpy.ndarray和阈值，返回numpy.ndarray
        vocoder_fn: 声码器函数，接受torch.Tensor，返回torch.Tensor
        campplus_model: CAMPPlus说话人识别模型
        mel_fn: Mel频谱提取函数，接受torch.Tensor，返回torch.Tensor
        mel_fn_args: Mel频谱参数字典
    """
    model: Any  # DiT模型，类型复杂，使用Any
    semantic_fn: Callable[[torch.Tensor], torch.Tensor]  # 语义特征提取函数
    vocoder_fn: Callable[[torch.Tensor], torch.Tensor]  # 声码器函数
    campplus_model: Any  # CAMPPlus模型，类型复杂，使用Any
    mel_fn: Callable[[torch.Tensor], torch.Tensor]  # Mel频谱提取函数
    mel_fn_args: Dict[str, Any]  # Mel频谱参数字典
    f0_fn: Optional[Callable[[Any, float], Any]] = None  # F0提取函数（可选）

