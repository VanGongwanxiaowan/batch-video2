import os
import sys
import threading
from pathlib import Path

import torch
import yaml
from diffusers import FluxPipeline

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("image_gen.ai_image_gen.flux", log_to_file=False)

CONFIG_PATH = "config/config.yaml"

try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    LORAS_BASE_PATH = config['paths']['lora_base_path']
    DEV_PATH = config['paths']['dev_path']
    DEFAULT_DEVICE_ID = config['settings']['device_id'] # Get default device ID from config
    LORA_NAME = config['settings']['lora_name']
    LORA_STEP = int(config['settings']['lora_step'])

except FileNotFoundError:
    logger.error(f"Error: Configuration file not found at {CONFIG_PATH}")
    # Handle error - using default paths
    LORAS_BASE_PATH = "/data2/home/wanheng/ComfyUI/models/loras/fluxloras" # Default
    DEV_PATH = "/data2/home/wanheng/shortmovie/backend/flux/flux-1-dev" # Default
    DEFAULT_DEVICE_ID = "0" # Default device ID
    LORA_NAME = None
    LORA_STEP = 120
except KeyError as e:
    logger.error(f"Error: Missing key in configuration file: {e}")
    # Handle error - using default paths
    LORAS_BASE_PATH = "/data2/home/wanheng/ComfyUI/models/loras/fluxloras" # Default
    DEV_PATH = "/data2/home/wanheng/shortmovie/backend/flux/flux-1-dev" # Default
    DEFAULT_DEVICE_ID = "0" # Default device ID
    LORA_NAME = None 
    LORA_STEP = 120
def load_pipe(deviceid: str = DEFAULT_DEVICE_ID): # Use default device ID from config
    # pipelock.acquire()
    pipe = None
    try:
        dev_path = DEV_PATH
        device_map = f"cuda:{deviceid}"
        logger.debug(f"device_map: {device_map}")
        pipe = FluxPipeline.from_pretrained(dev_path, torch_dtype=torch.bfloat16)
        pipe.to(device_map) # Move pipe to device after loading
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
