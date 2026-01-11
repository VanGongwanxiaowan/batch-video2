import io
import os
import sys
import traceback
from pathlib import Path

import torch
from diffusers import FluxPipeline
from fastapi import FastAPI, Response
from PIL import Image
from pydantic import BaseModel

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# Assuming tools.flux is in the parent directory
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import flux  # Import the flux module to access LORAS_BASE_PATH
from flux import load_pipe  # Still need load_pipe specifically

# 配置日志
logger = setup_logging("image_gen.flux_server.main", log_to_file=False)

app = FastAPI()

# Global variable to hold the loaded pipeline
pipe = None

class PromptRequest(BaseModel):
    prompt: str
    num_inference_steps: int = 30
    width: int = 1360
    height: int = 768

lora_path = None
@app.on_event("startup")
async def startup_event():
    """Load the Flux pipeline on application startup."""
    global pipe
    logger.info("Loading Flux pipeline")
    pipe = load_pipe()
    global lora_path
    if pipe:
        logger.info("Flux pipeline loaded successfully.")
        # Load all available LoRAs at startup
        if flux.LORA_NAME:
            lora_name = flux.LORA_NAME
            logger.debug(f"LoRA name: {flux.LORA_NAME}")
            lora_path = os.path.join(flux.LORAS_BASE_PATH, flux.LORA_NAME+'.safetensors')
            logger.debug(f"LoRA path: {lora_path}")
            if os.path.exists(lora_path):
                pipe.load_lora_weights(lora_path, adapter_name=lora_name)
                pipe.set_adapters(lora_name, flux.LORA_STEP / 100)
                logger.info(f"Loaded LoRA: {lora_name}")
            else:
                # pipe.set_adapters(None) 
                logger.warning(f"Loaded LoRA failed: no {lora_path}")

        else:
            # pipe.set_adapters(None) 
            logger.warning(f"LoRA base path not found: {flux.LORAS_BASE_PATH}")
    else:
        logger.error("Failed to load Flux pipeline.")

@app.post("/generate_image/")
async def generate_image(request: PromptRequest):
    """Generate an image from a text prompt."""
    if pipe is None:
        return {"error": "Flux pipeline not loaded. Check server startup logs."}

    try:
        # Run inference in a separate thread to avoid blocking the event loop
        # and use BytesIO to avoid disk I/O
        def _inference():
            image = pipe(
                request.prompt,
                num_inference_steps=request.num_inference_steps,
                width=request.width,
                height=request.height,
                # generator=torch.Generator(f"cuda:{request.device_id}").manual_seed(random.randint(0, 1000000000)) # Add seed if needed
            ).images[0]
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            return img_byte_arr

        # Use starlette's run_in_threadpool to run blocking code in a separate thread
        from starlette.concurrency import run_in_threadpool
        img_byte_arr = await run_in_threadpool(_inference)
        
        return Response(content=img_byte_arr.getvalue(), media_type="image/png")

    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 其他异常（图像生成错误等）
        logger.exception(f"[generate_image] Error during image generation: {e}")
        return {"error": str(e)}

# To run this app, you would typically use a command like:
# uvicorn flux.main:app --reload --port 8000
# You can set the lora_base_path environment variable before running
# export LORA_BASE_PATH="/path/to/your/loras"
# uvicorn flux.main:app --reload --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)