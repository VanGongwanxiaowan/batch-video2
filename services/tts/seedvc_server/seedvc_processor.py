"""
SeedVC语音克隆处理器模块
提供语音克隆的核心处理逻辑
"""
import os
from pathlib import Path
from typing import Optional, Tuple

import librosa
import numpy as np
import torch
import torchaudio

from core.exceptions import FileException, FileNotFoundException
from core.logging_config import setup_logging

from .seedvc_config import (
    F0_EPSILON,
    F0_THRESHOLD,
    HOP_LENGTH_NO_F0,
    HOP_LENGTH_WITH_F0,
    LONG_AUDIO_CHUNK_DURATION,
    LONG_AUDIO_OVERLAP_DURATION,
    MAX_REF_AUDIO_DURATION,
    OVERLAP_FRAME_LEN,
    SAMPLE_RATE_16K,
    SAMPLE_RATE_22K,
    SAMPLE_RATE_44K,
    SeedVCConfig,
    SeedVCModelConfig,
)


# 延迟导入，避免循环依赖
def _get_crossfade():
    """获取crossfade函数"""
    # 这些函数在 seedvc_run.py 中定义
    import sys
    from pathlib import Path
    seedvc_run_path = Path(__file__).parent / "seedvc_run.py"
    if seedvc_run_path.exists():
        # 动态导入，避免循环依赖
        import importlib.util
        spec = importlib.util.spec_from_file_location("seedvc_run", seedvc_run_path)
        seedvc_run = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seedvc_run)
        return seedvc_run.crossfade
    # 如果找不到，尝试从模块导入
    try:
        from modules.openvoice.utils import crossfade
        return crossfade
    except ImportError:
        raise ImportError("无法导入 crossfade 函数")

def _get_adjust_f0_semitones():
    """获取adjust_f0_semitones函数"""
    # 这些函数在 seedvc_run.py 中定义
    import sys
    from pathlib import Path
    seedvc_run_path = Path(__file__).parent / "seedvc_run.py"
    if seedvc_run_path.exists():
        # 动态导入，避免循环依赖
        import importlib.util
        spec = importlib.util.spec_from_file_location("seedvc_run", seedvc_run_path)
        seedvc_run = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(seedvc_run)
        return seedvc_run.adjust_f0_semitones
    # 如果找不到，尝试从模块导入
    try:
        from modules.openvoice.utils import adjust_f0_semitones
        return adjust_f0_semitones
    except ImportError:
        raise ImportError("无法导入 adjust_f0_semitones 函数")

logger = setup_logging("tts.seedvc_server.processor")


class SeedVCProcessor:
    """SeedVC语音克隆处理器
    
    负责执行语音克隆的各个步骤，将原来的 seedvc_clone 函数拆分为多个方法。
    """
    
    def __init__(self, config: SeedVCConfig, model_config: SeedVCModelConfig, device: torch.device, fp16: bool = False):
        """
        初始化处理器
        
        Args:
            config: 语音克隆配置
            model_config: 模型配置
            device: 计算设备
            fp16: 是否使用半精度浮点数
        """
        self.config = config
        self.model_config = model_config
        self.device = device
        self.fp16 = fp16
    
    def validate_inputs(self) -> None:
        """验证输入文件
        
        Raises:
            FileNotFoundException: 如果文件不存在
        """
        if not os.path.exists(self.config.source):
            raise FileNotFoundException(self.config.source)
        if not os.path.exists(self.config.target):
            raise FileNotFoundException(self.config.target)
        logger.info(f"输入文件验证通过: source={self.config.source}, target={self.config.target}")
    
    def load_audio_files(self) -> Tuple[torch.Tensor, torch.Tensor, int]:
        """加载音频文件
        
        Returns:
            (source_audio, ref_audio, sampling_rate): 源音频、参考音频和采样率
            
        Raises:
            FileException: 如果加载失败
        """
        try:
            sr = self.model_config.mel_fn_args['sampling_rate']
            
            logger.debug(f"加载源音频: {self.config.source}")
            source_audio, _ = librosa.load(self.config.source, sr=sr)
            
            logger.debug(f"加载目标音频: {self.config.target}")
            ref_audio, _ = librosa.load(self.config.target, sr=sr)
            
            # 根据F0条件调整采样率
            if self.config.f0_condition:
                sr = SAMPLE_RATE_44K
                hop_length = HOP_LENGTH_WITH_F0
            else:
                sr = SAMPLE_RATE_22K
                hop_length = HOP_LENGTH_NO_F0
            
            # 转换为张量
            source_audio = torch.tensor(source_audio).unsqueeze(0).float().to(self.device)
            ref_audio = torch.tensor(ref_audio[:sr * MAX_REF_AUDIO_DURATION]).unsqueeze(0).float().to(self.device)
            
            return source_audio, ref_audio, sr
            
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (FileNotFoundError, OSError, IOError) as e:
            # 文件系统错误
            raise FileException(f"加载音频文件失败: {e}") from e
        except (ValueError, RuntimeError) as e:
            # 音频处理错误
            raise FileException(f"加载音频文件失败: {e}") from e
        except Exception as e:
            # 其他未预期的异常
            raise FileException(f"加载音频文件失败: {e}") from e
    
    def extract_semantic_features(self, source_audio: torch.Tensor, sr: int) -> torch.Tensor:
        """提取语义特征
        
        Args:
            source_audio: 源音频张量
            sr: 采样率
            
        Returns:
            语义特征张量
        """
        logger.debug("重采样源音频到 16kHz")
        converted_waves_16k = torchaudio.functional.resample(source_audio, sr, SAMPLE_RATE_16K)
        
        logger.debug("提取源音频语义特征")
        if converted_waves_16k.size(-1) <= SAMPLE_RATE_16K * LONG_AUDIO_CHUNK_DURATION:
            S_alt = self.model_config.semantic_fn(converted_waves_16k)
        else:
            # 处理长音频：分块处理
            logger.debug("源音频较长，使用分块处理")
            S_alt = self._process_long_audio(converted_waves_16k)
        
        return S_alt
    
    def _process_long_audio(self, converted_waves_16k: torch.Tensor) -> torch.Tensor:
        """处理长音频的分块逻辑
        
        Args:
            converted_waves_16k: 16kHz的音频张量
            
        Returns:
            拼接后的语义特征
        """
        S_alt_list = []
        buffer = None
        traversed_time = 0
        
        chunk_size = SAMPLE_RATE_16K * LONG_AUDIO_CHUNK_DURATION
        overlap_size = SAMPLE_RATE_16K * LONG_AUDIO_OVERLAP_DURATION
        overlap_frames = 50 * LONG_AUDIO_OVERLAP_DURATION
        
        while traversed_time < converted_waves_16k.size(-1):
            if buffer is None:  # 第一块
                chunk = converted_waves_16k[:, traversed_time:traversed_time + chunk_size]
            else:
                chunk = torch.cat(
                    [
                        buffer,
                        converted_waves_16k[:, traversed_time:traversed_time + chunk_size - overlap_size]
                    ],
                    dim=-1
                )
            
            S_alt = self.model_config.semantic_fn(chunk)
            
            if traversed_time == 0:
                S_alt_list.append(S_alt)
            else:
                S_alt_list.append(S_alt[:, overlap_frames:])
            
            buffer = chunk[:, -overlap_size:]
            traversed_time += chunk_size if traversed_time == 0 else chunk.size(-1) - overlap_size
        
        return torch.cat(S_alt_list, dim=1)
    
    def extract_reference_features(self, ref_audio: torch.Tensor, sr: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """提取参考音频特征
        
        Args:
            ref_audio: 参考音频张量
            sr: 采样率
            
        Returns:
            (semantic_features, speaker_features): 语义特征和说话人特征
        """
        logger.debug("提取参考音频特征")
        ori_waves_16k = torchaudio.functional.resample(ref_audio, sr, SAMPLE_RATE_16K)
        S_ori = self.model_config.semantic_fn(ori_waves_16k)
        
        # 提取说话人特征
        logger.debug("提取说话人特征")
        feat2 = torchaudio.compliance.kaldi.fbank(
            ori_waves_16k,
            num_mel_bins=80,
            dither=0,
            sample_frequency=SAMPLE_RATE_16K
        )
        feat2 = feat2 - feat2.mean(dim=0, keepdim=True)
        style2 = self.model_config.campplus_model(feat2.unsqueeze(0))
        
        return S_ori, style2
    
    def extract_f0_features(
        self,
        source_audio_16k: torch.Tensor,
        ref_audio_16k: torch.Tensor
    ) -> Tuple[Optional[torch.Tensor], Optional[torch.Tensor], Optional[torch.Tensor]]:
        """提取F0特征（如果启用）
        
        Args:
            source_audio_16k: 16kHz源音频
            ref_audio_16k: 16kHz参考音频
            
        Returns:
            (F0_ori, F0_alt, shifted_f0_alt): F0特征
        """
        if not self.config.f0_condition or self.model_config.f0_fn is None:
            return None, None, None
        
        logger.debug("处理 F0 特征")
        F0_ori = self.model_config.f0_fn(ref_audio_16k[0], thred=F0_THRESHOLD)
        F0_alt = self.model_config.f0_fn(source_audio_16k[0], thred=F0_THRESHOLD)
        
        F0_ori = torch.from_numpy(F0_ori).to(self.device)[None]
        F0_alt = torch.from_numpy(F0_alt).to(self.device)[None]
        
        shifted_f0_alt = self._adjust_f0(F0_alt, F0_ori)
        
        return F0_ori, F0_alt, shifted_f0_alt
    
    def _adjust_f0(self, F0_alt: torch.Tensor, F0_ori: torch.Tensor) -> torch.Tensor:
        """调整F0特征
        
        Args:
            F0_alt: 源音频F0
            F0_ori: 参考音频F0
            
        Returns:
            调整后的F0
        """
        voiced_F0_ori = F0_ori[F0_ori > 1]
        voiced_F0_alt = F0_alt[F0_alt > 1]
        
        log_f0_alt = torch.log(F0_alt + F0_EPSILON)
        voiced_log_f0_ori = torch.log(voiced_F0_ori + F0_EPSILON)
        voiced_log_f0_alt = torch.log(voiced_F0_alt + F0_EPSILON)
        median_log_f0_ori = torch.median(voiced_log_f0_ori)
        median_log_f0_alt = torch.median(voiced_log_f0_alt)
        
        shifted_log_f0_alt = log_f0_alt.clone()
        if self.config.auto_f0_adjust:
            shifted_log_f0_alt[F0_alt > 1] = (
                log_f0_alt[F0_alt > 1] - median_log_f0_alt + median_log_f0_ori
            )
        
        shifted_f0_alt = torch.exp(shifted_log_f0_alt)
        
        if self.config.pitch_shift != 0:
            # 延迟导入，避免循环依赖
            from .seedvc_run import adjust_f0_semitones
            shifted_f0_alt[F0_alt > 1] = adjust_f0_semitones(
                shifted_f0_alt[F0_alt > 1].cpu().numpy(),
                self.config.pitch_shift
            )
            shifted_f0_alt[F0_alt > 1] = torch.from_numpy(
                shifted_f0_alt[F0_alt > 1].cpu().numpy()
            ).to(self.device)
        
        return shifted_f0_alt
    
    def process_audio(
        self,
        S_alt: torch.Tensor,
        S_ori: torch.Tensor,
        style2: torch.Tensor,
        source_audio: torch.Tensor,
        ref_audio: torch.Tensor,
        shifted_f0_alt: Optional[torch.Tensor],
        F0_ori: Optional[torch.Tensor],
        sr: int
    ) -> torch.Tensor:
        """处理音频生成
        
        Args:
            S_alt: 源音频语义特征
            S_ori: 参考音频语义特征
            style2: 说话人特征
            source_audio: 源音频
            ref_audio: 参考音频
            shifted_f0_alt: 调整后的F0（可选）
            F0_ori: 参考F0（可选）
            sr: 采样率
            
        Returns:
            生成的音频波形
        """
        # 计算Mel频谱
        logger.debug("计算 Mel 频谱")
        mel = self.model_config.mel_fn(source_audio.to(self.device).float())
        mel2 = self.model_config.mel_fn(ref_audio.to(self.device).float())
        target_lengths = torch.LongTensor([int(mel.size(2) * self.config.length_adjust)]).to(mel.device)
        target2_lengths = torch.LongTensor([mel2.size(2)]).to(mel2.device)
        
        # 长度调节
        logger.debug("执行长度调节")
        cond, _, codes, commitment_loss, codebook_loss = self.model_config.model.length_regulator(
            S_alt,
            ylens=target_lengths,
            n_quantizers=3,
            f0=shifted_f0_alt
        )
        prompt_condition, _, codes, commitment_loss, codebook_loss = self.model_config.model.length_regulator(
            S_ori,
            ylens=target2_lengths,
            n_quantizers=3,
            f0=F0_ori
        )
        
        # 分块生成
        hop_length = HOP_LENGTH_WITH_F0 if self.config.f0_condition else HOP_LENGTH_NO_F0
        max_context_window = sr // hop_length * LONG_AUDIO_CHUNK_DURATION
        overlap_frame_len = OVERLAP_FRAME_LEN
        overlap_wave_len = overlap_frame_len * hop_length
        
        logger.debug("开始分块生成音频")
        max_source_window = max_context_window - mel2.size(2)
        processed_frames = 0
        generated_wave_chunks = []
        previous_chunk = None
        
        while processed_frames < cond.size(1):
            chunk_cond = cond[:, processed_frames:processed_frames + max_source_window]
            is_last_chunk = processed_frames + max_source_window >= cond.size(1)
            cat_condition = torch.cat([prompt_condition, chunk_cond], dim=1)
            
            with torch.autocast(
                device_type=self.device.type,
                dtype=torch.float16 if self.fp16 else torch.float32
            ):
                # 语音转换
                vc_target = self.model_config.model.cfm.inference(
                    cat_condition,
                    torch.LongTensor([cat_condition.size(1)]).to(mel2.device),
                    mel2,
                    style2,
                    None,
                    self.config.diffusion_steps,
                    inference_cfg_rate=self.config.inference_cfg_rate
                )
                vc_target = vc_target[:, :, mel2.size(-1):]
            
            vc_wave = self.model_config.vocoder_fn(vc_target.float()).squeeze()
            vc_wave = vc_wave[None, :]
            
            # 处理分块拼接
            if processed_frames == 0:
                if is_last_chunk:
                    output_wave = vc_wave[0].cpu().numpy()
                    generated_wave_chunks.append(output_wave)
                    break
                output_wave = vc_wave[0, :-overlap_wave_len].cpu().numpy()
                generated_wave_chunks.append(output_wave)
                previous_chunk = vc_wave[0, -overlap_wave_len:]
                processed_frames += vc_target.size(2) - overlap_frame_len
            elif is_last_chunk:
                # 延迟导入，避免循环依赖
                from .seedvc_run import crossfade
                output_wave = crossfade(
                    previous_chunk.cpu().numpy(),
                    vc_wave[0].cpu().numpy(),
                    overlap_wave_len
                )
                generated_wave_chunks.append(output_wave)
                processed_frames += vc_target.size(2) - overlap_frame_len
                break
            else:
                # 延迟导入，避免循环依赖
                from .seedvc_run import crossfade
                output_wave = crossfade(
                    previous_chunk.cpu().numpy(),
                    vc_wave[0, :-overlap_wave_len].cpu().numpy(),
                    overlap_wave_len
                )
                generated_wave_chunks.append(output_wave)
                previous_chunk = vc_wave[0, -overlap_wave_len:]
                processed_frames += vc_target.size(2) - overlap_frame_len
        
        # 合并所有块
        vc_wave = torch.tensor(np.concatenate(generated_wave_chunks))[None, :].float()
        return vc_wave
    
    def save_output(self, vc_wave: torch.Tensor, sr: int) -> None:
        """保存输出文件
        
        Args:
            vc_wave: 生成的音频波形
            sr: 采样率
            
        Raises:
            FileException: 如果保存失败
        """
        try:
            logger.debug(f"保存输出文件: {self.config.output}")
            output_path = Path(self.config.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(str(output_path), vc_wave.cpu(), sr)
            logger.info(f"输出文件已保存: {self.config.output}")
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, IOError) as e:
            # 文件系统错误
            raise FileException(f"保存输出文件失败: {e}") from e
        except (RuntimeError, ValueError) as e:
            # 运行时错误或数据格式错误
            raise FileException(f"保存输出文件失败: {e}") from e
        except Exception as e:
            # 其他未预期的异常
            raise FileException(f"保存输出文件失败: {e}") from e

