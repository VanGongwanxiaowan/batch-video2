import os
import sys
import threading
from pathlib import Path

import torch
from diffusers import FluxPipeline

from config import flux_settings

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("image_gen.flux_server.flux", log_to_file=False)

# [Optimization] Enable TF32 for faster matrix multiplications on Ampere+ GPUs
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

LORAS_BASE_PATH = str(flux_settings.lora_base_path)
DEV_PATH = str(flux_settings.model_path)
DEFAULT_DEVICE_ID = flux_settings.FLUX_DEVICE_ID
LORA_NAME = flux_settings.FLUX_LORA_NAME
LORA_STEP = int(flux_settings.FLUX_LORA_STEP)
def load_pipe(deviceid: str = DEFAULT_DEVICE_ID): # Use default device ID from config
    # pipelock.acquire()
    pipe = None
    try:
        dev_path = DEV_PATH
        # device_map = f"cuda:{deviceid}"
        # logger.debug(f"device_map: {device_map}")
        
        # Load pipeline without moving to CUDA immediately
        # [Optimization] Ensure strictly bfloat16 to avoid float32 fallback overhead
        pipe = FluxPipeline.from_pretrained(dev_path, torch_dtype=torch.bfloat16)
        
        # Use CPU offload to save VRAM (crucial for Flux)
        # This will automatically move components to GPU when needed and back to CPU
        pipe.enable_model_cpu_offload(device=f"cuda:{deviceid}")
        
        # [Optimization] Enable VAE tiling to save VRAM during decoding of large images
        pipe.enable_vae_tiling()

        # [Optimization] Torch Compile
        # Use torch.compile to optimize the transformer. 
        # mode="reduce-overhead" reduces CUDA graph overhead, good for inference loops.
        # Note: First inference will be slow due to compilation.
        if hasattr(torch, "compile"):
            try:
                logger.info("Compiling Flux transformer with torch.compile (mode='reduce-overhead')...")
                # Flux uses 'transformer', not 'unet'
                pipe.transformer = torch.compile(pipe.transformer, mode="reduce-overhead")
                # Optional: Compile VAE decoder if needed, but it might be small enough
                # pipe.vae.decode = torch.compile(pipe.vae.decode, mode="reduce-overhead")
                logger.info("Flux transformer compilation configured.")
            except Exception as e:
                logger.warning(f"Failed to apply torch.compile: {e}")
        
        # [Optimization] Check Attention mechanism
        # Diffusers >= 0.29.0 automatically uses SDPA (scaled_dot_product_attention) 
        # if torch >= 2.0 is available.
        logger.info(f"PyTorch version: {torch.__version__}")
        
        # Optional: Enable sequential cpu offload for even lower memory usage (slower)
        # pipe.enable_sequential_cpu_offload(device=f"cuda:{deviceid}")
        
        # pipe.to(device_map) # Replaced by cpu_offload
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, FileNotFoundError) as e:
        # 文件系统错误或模型文件不存在
        logger.error(f"[load_flux_model] 文件系统错误，加载 Flux 模型失败：{e}", exc_info=True)
    except Exception as e:
        # 其他异常（模型加载错误等）
        logger.exception(f"[load_flux_model] 加载 Flux 模型失败：{e}")
    finally:
        # pipelock.release()
        return pipe
