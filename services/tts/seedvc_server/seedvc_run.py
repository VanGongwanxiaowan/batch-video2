# -*- coding: utf-8 -*-
"""
SeedVC 语音克隆核心模块
提供模型加载和语音克隆功能
"""
import os
import sys
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

if TYPE_CHECKING:
    from .seedvc_config import SeedVCConfig, SeedVCModelConfig

import librosa
import numpy as np
import torch
import torchaudio
import yaml

# 设置环境变量
os.environ['HF_HUB_CACHE'] = './checkpoints/hf_cache'
warnings.simplefilter('ignore')

# 导入项目模块
from common import build_model, load_checkpoint, recursive_munch

# 导入日志配置
from core.logging_config import setup_logging

logger = setup_logging("tts.seedvc_server.run")

# 设备选择
if torch.cuda.is_available():
    device = torch.device("cuda")
    logger.info("使用 CUDA 设备")
elif torch.backends.mps.is_available():
    device = torch.device("mps")
    logger.info("使用 MPS 设备")
else:
    device = torch.device("cpu")
    logger.info("使用 CPU 设备")

# 全局配置
fp16 = False

# 默认模型路径配置
DEFAULT_MODEL_PATHS = {
    'dit_checkpoint': 'models/DiT_seed_v2_uvit_whisper_small_wavenet_bigvgan_pruned.pth',
    'dit_config': 'models/config_dit_mel_seed_uvit_whisper_small_wavenet.yml',
    'campplus_checkpoint': 'models/campplus_cn_common.bin',
    'bigvgan_model': 'models/bigvgan_v2_22khz_80band_256x',
    'whisper_model': 'models/whisper-small',
}


def load_models(
    checkpoint: Optional[str] = None,
    config: Optional[str] = None,
    model_base_path: Optional[str] = None
) -> Tuple:
    """
    加载所有必需的模型
    
    Args:
        checkpoint: 可选的检查点路径（未使用，保留兼容性）
        config: 可选的配置文件路径
        model_base_path: 模型基础路径，如果提供则覆盖默认路径
        
    Returns:
        Tuple: (model, semantic_fn, f0_fn, vocoder_fn, campplus_model, to_mel, mel_fn_args)
        
    Raises:
        FileNotFoundError: 如果模型文件不存在
        RuntimeError: 如果模型加载失败
    """
    global fp16
    fp16 = True
    
    try:
        # 确定模型路径
        base_path = Path(model_base_path) if model_base_path else Path('.')
        dit_checkpoint_path = base_path / DEFAULT_MODEL_PATHS['dit_checkpoint']
        dit_config_path = base_path / (config or DEFAULT_MODEL_PATHS['dit_config'])
        campplus_ckpt_path = base_path / DEFAULT_MODEL_PATHS['campplus_checkpoint']
        bigvgan_model_path = base_path / DEFAULT_MODEL_PATHS['bigvgan_model']
        whisper_model_path = base_path / DEFAULT_MODEL_PATHS['whisper_model']
        
        # 验证文件存在
        for path, name in [
            (dit_checkpoint_path, 'DiT checkpoint'),
            (dit_config_path, 'DiT config'),
            (campplus_ckpt_path, 'CAMPPlus checkpoint'),
            (bigvgan_model_path, 'BigVGAN model'),
            (whisper_model_path, 'Whisper model'),
        ]:
            if not path.exists():
                raise FileNotFoundError(f"{name} 文件不存在: {path}")
        
        logger.info(f"加载 DiT 配置文件: {dit_config_path}")
        with open(dit_config_path, "r", encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        model_params = recursive_munch(config_dict["model_params"])
        model_params.dit_type = 'DiT'
        
        logger.info("构建 DiT 模型...")
        model = build_model(model_params, stage="DiT")
        
        hop_length = config_dict["preprocess_params"]["spect_params"]["hop_length"]
        sr = config_dict["preprocess_params"]["sr"]
        
        # 加载检查点
        logger.info(f"加载 DiT 检查点: {dit_checkpoint_path}")
        model, _, _, _ = load_checkpoint(
            model,
            None,
            str(dit_checkpoint_path),
            load_only_params=True,
            ignore_modules=[],
            is_distributed=False,
        )
        
        for key in model:
            model[key].eval()
            model[key].to(device)
        
        model.cfm.estimator.setup_caches(max_batch_size=1, max_seq_length=8192)
        logger.info("DiT 模型加载完成")
        
        # 加载 CAMPPlus 模型
        logger.info(f"加载 CAMPPlus 模型: {campplus_ckpt_path}")
        from modules.campplus.DTDNN import CAMPPlus
        
        campplus_model = CAMPPlus(feat_dim=80, embedding_size=192)
        campplus_model.load_state_dict(
            torch.load(str(campplus_ckpt_path), map_location="cpu")
        )
        campplus_model.eval()
        campplus_model.to(device)
        logger.info("CAMPPlus 模型加载完成")
        
        # 加载 Vocoder
        vocoder_type = model_params.vocoder.type
        if vocoder_type == 'bigvgan':
            logger.info(f"加载 BigVGAN 模型: {bigvgan_model_path}")
            from modules.bigvgan import bigvgan
            
            bigvgan_model = bigvgan.BigVGAN.from_pretrained(
                str(bigvgan_model_path),
                use_cuda_kernel=False
            )
            bigvgan_model.remove_weight_norm()
            bigvgan_model = bigvgan_model.eval().to(device)
            vocoder_fn = bigvgan_model
            logger.info("BigVGAN 模型加载完成")
        else:
            raise ValueError(f"不支持的 vocoder 类型: {vocoder_type}")
        
        # 加载 Whisper 模型
        speech_tokenizer_type = model_params.speech_tokenizer.type
        if speech_tokenizer_type == 'whisper':
            logger.info(f"加载 Whisper 模型: {whisper_model_path}")
            from transformers import AutoFeatureExtractor, WhisperModel
            
            whisper_model = WhisperModel.from_pretrained(
                str(whisper_model_path),
                torch_dtype=torch.float16
            ).to(device)
            del whisper_model.decoder
            whisper_feature_extractor = AutoFeatureExtractor.from_pretrained(
                str(whisper_model_path)
            )
            
            def semantic_fn(waves_16k):
                """Whisper 语义特征提取函数"""
                try:
                    ori_inputs = whisper_feature_extractor(
                        [waves_16k.squeeze(0).cpu().numpy()],
                        return_tensors="pt",
                        return_attention_mask=True
                    )
                    ori_input_features = whisper_model._mask_input_features(
                        ori_inputs.input_features,
                        attention_mask=ori_inputs.attention_mask
                    ).to(device)
                    
                    with torch.no_grad():
                        ori_outputs = whisper_model.encoder(
                            ori_input_features.to(whisper_model.encoder.dtype),
                            head_mask=None,
                            output_attentions=False,
                            output_hidden_states=False,
                            return_dict=True,
                        )
                    S_ori = ori_outputs.last_hidden_state.to(torch.float32)
                    S_ori = S_ori[:, :waves_16k.size(-1) // 320 + 1]
                    return S_ori
                except (SystemExit, KeyboardInterrupt):
                    # 系统退出异常，不捕获，直接抛出
                    raise
                except (RuntimeError, OSError) as e:
                    # 运行时错误或文件IO错误
                    logger.error(f"[load_models] Whisper 特征提取失败: {e}", exc_info=True)
                    raise
                except Exception as e:
                    # 其他未预期的异常
                    logger.error(f"[load_models] Whisper 特征提取失败: {e}", exc_info=True)
                    raise RuntimeError(f"Whisper 特征提取失败: {e}") from e
            
            logger.info("Whisper 模型加载完成")
        else:
            raise ValueError(f"不支持的 speech_tokenizer 类型: {speech_tokenizer_type}")
        
        # 配置 Mel 频谱函数
        mel_fn_args = {
            "n_fft": config_dict['preprocess_params']['spect_params']['n_fft'],
            "win_size": config_dict['preprocess_params']['spect_params']['win_length'],
            "hop_size": config_dict['preprocess_params']['spect_params']['hop_length'],
            "num_mels": config_dict['preprocess_params']['spect_params']['n_mels'],
            "sampling_rate": sr,
            "fmin": config_dict['preprocess_params']['spect_params'].get('fmin', 0),
            "fmax": None if config_dict['preprocess_params']['spect_params'].get('fmax', "None") == "None" else 8000,
            "center": False
        }
        
        from modules.audio import mel_spectrogram
        to_mel = lambda x: mel_spectrogram(x, **mel_fn_args)
        
        f0_fn = None  # F0 功能当前未使用
        
        logger.info("所有模型加载完成")
        return (
            model,
            semantic_fn,
            f0_fn,
            vocoder_fn,
            campplus_model,
            to_mel,
            mel_fn_args,
        )
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except FileNotFoundError as e:
        logger.error(f"[load_models] 模型文件未找到: {e}", exc_info=True)
        raise
    except (OSError, PermissionError) as e:
        # 文件系统错误
        logger.error(f"[load_models] 文件系统错误: {e}", exc_info=True)
        raise RuntimeError(f"模型加载失败: {e}") from e
    except (RuntimeError, ImportError, AttributeError) as e:
        # 运行时错误、导入错误或属性错误
        logger.error(f"[load_models] 运行时错误: {e}", exc_info=True)
        raise RuntimeError(f"模型加载失败: {e}") from e
    except Exception as e:
        # 其他未预期的异常
        logger.error(f"[load_models] 模型加载失败: {e}", exc_info=True)
        raise RuntimeError(f"模型加载失败: {e}") from e


def adjust_f0_semitones(f0_sequence: np.ndarray, n_semitones: float) -> np.ndarray:
    """
    调整 F0 序列的音高（半音）
    
    Args:
        f0_sequence: F0 序列
        n_semitones: 半音调整量
        
    Returns:
        调整后的 F0 序列
    """
    factor = 2 ** (n_semitones / 12)
    return f0_sequence * factor


def crossfade(chunk1: np.ndarray, chunk2: np.ndarray, overlap: int) -> np.ndarray:
    """
    交叉淡化两个音频块
    
    Args:
        chunk1: 第一个音频块
        chunk2: 第二个音频块
        overlap: 重叠长度
        
    Returns:
        交叉淡化后的音频块
    """
    fade_out = np.cos(np.linspace(0, np.pi / 2, overlap)) ** 2
    fade_in = np.cos(np.linspace(np.pi / 2, 0, overlap)) ** 2
    
    if len(chunk2) < overlap:
        chunk2[:overlap] = (
            chunk2[:overlap] * fade_in[:len(chunk2)] +
            (chunk1[-overlap:] * fade_out)[:len(chunk2)]
        )
    else:
        chunk2[:overlap] = (
            chunk2[:overlap] * fade_in +
            chunk1[-overlap:] * fade_out
        )
    return chunk2


@torch.no_grad()
def seedvc_clone(
    model: Any,
    semantic_fn: Callable[[torch.Tensor], torch.Tensor],
    f0_fn: Optional[Callable[[Any, float], Any]],
    vocoder_fn: Callable[[torch.Tensor], torch.Tensor],
    campplus_model: Any,
    mel_fn: Callable[[torch.Tensor], torch.Tensor],
    mel_fn_args: Dict[str, Any],
    source: str,
    target: str,
    diffusion_steps: int = 30,
    length_adjust: float = 1.0,
    inference_cfg_rate: float = 0.7,
    output: str = 'sed_test.wav'
) -> None:
    """
    执行语音克隆（向后兼容接口）。
    
    此函数保留用于向后兼容，新代码应使用 `seedvc_clone_with_config`。
    
    Args:
        model: DiT 模型
        semantic_fn: 语义特征提取函数
        f0_fn: F0 提取函数（可选）
        vocoder_fn: 声码器函数
        campplus_model: CAMPPlus 说话人识别模型
        mel_fn: Mel 频谱提取函数
        mel_fn_args: Mel 频谱参数
        source: 源音频文件路径
        target: 目标参考音频文件路径
        diffusion_steps: 扩散步数，默认30
        length_adjust: 长度调整因子，默认1.0
        inference_cfg_rate: 推理配置率，默认0.7
        output: 输出文件路径，默认'sed_test.wav'
        
    Raises:
        FileNotFoundError: 如果音频文件不存在
        RuntimeError: 如果处理失败
        
    Note:
        此函数将在未来版本中废弃，建议使用 `seedvc_clone_with_config`
    """
    from .seedvc_config import SeedVCConfig, SeedVCModelConfig
    from .seedvc_processor import SeedVCProcessor

    # 创建配置对象
    config = SeedVCConfig(
        source=source,
        target=target,
        output=output,
        diffusion_steps=diffusion_steps,
        length_adjust=length_adjust,
        inference_cfg_rate=inference_cfg_rate,
    )
    
    model_config = SeedVCModelConfig(
        model=model,
        semantic_fn=semantic_fn,
        f0_fn=f0_fn,
        vocoder_fn=vocoder_fn,
        campplus_model=campplus_model,
        mel_fn=mel_fn,
        mel_fn_args=mel_fn_args,
    )
    
    # 使用处理器执行
    seedvc_clone_with_config(config, model_config)


def seedvc_clone_with_config(config: "SeedVCConfig", model_config: "SeedVCModelConfig") -> None:  # type: ignore
    """
    使用配置对象执行语音克隆（推荐使用）。
    
    此函数使用配置数据类封装参数，提供更好的类型安全和可维护性。
    
    Args:
        config: 语音克隆配置对象
        model_config: 模型配置对象
        
    Raises:
        ValueError: 如果配置参数无效
        FileNotFoundException: 如果音频文件不存在
        RuntimeError: 如果处理失败
    """
    from .seedvc_config import SeedVCConfig, SeedVCModelConfig
    from .seedvc_processor import SeedVCProcessor
    
    try:
        # 验证配置
        config.validate()
        
        # 创建处理器
        processor = SeedVCProcessor(config, model_config, device, fp16)
        
        # 执行处理流程
        processor.validate_inputs()
        source_audio, ref_audio, sr = processor.load_audio_files()
        
        time_vc_start = time.time()
        
        # 提取特征
        S_alt = processor.extract_semantic_features(source_audio, sr)
        S_ori, style2 = processor.extract_reference_features(ref_audio, sr)
        
        # 提取F0特征（如果启用）
        source_audio_16k = torchaudio.functional.resample(source_audio, sr, 16000)
        ref_audio_16k = torchaudio.functional.resample(ref_audio, sr, 16000)
        F0_ori, F0_alt, shifted_f0_alt = processor.extract_f0_features(source_audio_16k, ref_audio_16k)
        
        # 处理音频生成
        vc_wave = processor.process_audio(
            S_alt, S_ori, style2, source_audio, ref_audio,
            shifted_f0_alt, F0_ori, sr
        )
        
        time_vc_end = time.time()
        rtf = (time_vc_end - time_vc_start) / (vc_wave.size(-1) / sr)
        logger.info(f"语音克隆完成，RTF: {rtf:.4f}")
        
        # 保存输出
        processor.save_output(vc_wave, sr)
        
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except FileNotFoundError as e:
        logger.error(f"[seedvc_clone_with_config] 文件未找到: {e}", exc_info=True)
        raise
    except Exception as e:
        # 其他异常（语音克隆错误等）
        logger.error(f"[seedvc_clone_with_config] 语音克隆失败: {e}", exc_info=True)
        raise RuntimeError(f"语音克隆失败: {e}") from e
