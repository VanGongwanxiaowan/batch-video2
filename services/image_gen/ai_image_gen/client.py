import asyncio
import json
import os
import random
import sys
import time
import uuid
from pathlib import Path

import httpx

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("image_gen.ai_image_gen.client", log_to_file=False)

class ImageClient:
    """
    A client for interacting with an image generation API.
    """
    BASE_URL = "http://localhost:8000"

    def __init__(self):
        # Initialize the client, no specific setup needed for now beyond BASE_URL
        pass

    def _generate_image_request_data(self, topic: str, model_name: str, custom_prompt: str, loras: list = None):
        """
        Generates sample image generation request data with a custom prompt and optional loras.
        This is an internal helper method.
        """
        task_id = str(uuid.uuid4())
        
        # Default values, which will be overridden by model-specific settings
        prompt = custom_prompt
        negative_prompt = "blurry, low quality"
        image_params = {"width": 512, "height": 512, "steps": 10, "cfg_scale": 2.0, "seed": -1, "batch_size": 1}
        
        # Use provided loras if available, otherwise use model-specific defaults
        final_loras = loras if loras is not None else []
        
        # Model-specific overrides for parameters if loras are not explicitly provided
        if model_name == "sd15":
            negative_prompt = "ugly, deformed"
            image_params = {"width": 512, "height": 512, "steps": 20, "cfg_scale": 7.0, "seed": -1, "batch_size": 1}
            if loras is None: # Only apply default loras if not provided by user
                final_loras = [{"name": "KoalaEngineV2a", "weight": 0.8}]
        elif model_name == "flux":
            negative_prompt = "cartoon, anime, low resolution"
            image_params = {
                "width": 1024,
                "height": 1024,
                "steps": 5,
                "cfg_scale": 6.0,
                "seed": -1, # Random seed
                "batch_size": 1
            }
            if loras is None: # Only apply default loras if not provided by user
                lora_name = random.choice(["擦边北岸纯欲性感脸模黛雅.beiansafetensors", "古风漫画男主", "测试卡通动画又红又专"])
                final_loras = [{"name": lora_name, "weight": 0.8}]

        request_data = {
            "user_id": "client_user_" + str(random.randint(1, 100)),
            "topic": topic, 
            "model_name": model_name,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "image_params": image_params,
            "loras": final_loras,
        }
        return request_data

    async def _submit_image_generation_task(self, client: httpx.AsyncClient, topic: str, model_name: str, prompt: str, loras: list = None):
        """
        Submits an image generation task to the API.
        This is an internal helper method.
        """
        data = self._generate_image_request_data(topic, model_name, prompt, loras)
        logger.info(f"Submitting task for topic: {topic}, model: {model_name} with prompt: {data['prompt'][:50]}...")
        try:
            response = await client.post(f"{self.BASE_URL}/generate_image", json=data)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Task submitted: {result}")
            return result.get("task_id"), topic, model_name
        except httpx.HTTPStatusError as e:
            logger.error(f"Error submitting task: {e.response.status_code} - {e.response.text}")
            return None, None, None
        except httpx.RequestError as e:
            logger.exception(f"Network error submitting task: {e}")
            return None, None, None

    async def _get_image_and_save(self, client: httpx.AsyncClient, task_id: str, topic: str, model_name: str, save_path: str):
        """
        Continuously calls get_image API and saves the image if successful.
        This is an internal helper method.
        """
        # Ensure the directory exists
        output_dir = os.path.dirname(save_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        while True:
            try:
                response = await client.get(f"{self.BASE_URL}/get_image/{task_id}")
                response.raise_for_status()
                
                # Determine file extension from content-type header or default to .png
                content_type = response.headers.get("content-type", "application/octet-stream")
                if "image/png" in content_type:
                    file_extension = "png"
                elif "image/jpeg" in content_type:
                    file_extension = "jpg"
                else:
                    file_extension = "bin" # Default for unknown types

                # If save_path doesn't have an extension, append one
                if not os.path.splitext(save_path)[1]:
                    final_save_path = f"{save_path}.{file_extension}"
                else:
                    final_save_path = save_path

                with open(final_save_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Successfully retrieved and saved image for task {task_id}.")
                logger.info(f"Task ID: {task_id}, Topic: {topic}, Model: {model_name}, File Path: {final_save_path}")
                break # Exit loop if image is successfully retrieved
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and "not completed" in e.response.text:
                    logger.debug(f"Task {task_id} not completed yet. Retrying in 1 second...")
                    await asyncio.sleep(1)
                elif e.response.status_code == 404 and "not found" in e.response.text:
                    logger.debug(f"Task {task_id} not found. Retrying in 1 second...")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"Error retrieving image for task {task_id}: {e.response.status_code} - {e.response.text}")
                    break # Exit on other errors
            except httpx.RequestError as e:
                logger.debug(f"Network error retrieving image for task {task_id}: {e}. Retrying in 1 second...")
                await asyncio.sleep(1)
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except Exception as e:
                # 其他异常（图像保存错误等）
                logger.exception(f"[get_image] An unexpected error occurred while saving image for task {task_id}: {e}")
                break

    async def draw_image(self, model_name: str, prompt: str, save_path: str = None, loras: list = None):
        """
        Draws an image using the specified model and prompt.
        Optionally saves the image to the given path and applies specified LoRAs.

        Args:
            model_name (str): The name of the image generation model (e.g., "sd15", "flux").
            prompt (str): The text prompt for image generation.
            save_path (str, optional): The full path to save the generated image. 
                                       If None, the image will not be saved locally,
                                       but the task ID will still be printed.
            loras (list, optional): A list of dictionaries, where each dictionary represents a LoRA
                                    and should contain "name" and "weight" keys.
                                    Example: [{"name": "MyLora", "weight": 0.7}]
                                    If None, default LoRAs for the model will be used (if any).
        """
        async with httpx.AsyncClient() as client:
            # For a single image, we can use a generic topic or infer one
            topic = f"single_image_request_{model_name}" 
            
            task_id, _, _ = await self._submit_image_generation_task(client, topic, model_name, prompt, loras)
            
            if task_id:
                if save_path:
                    logger.info(f"Attempting to retrieve and save image for task {task_id} to {save_path}...")
                    await self._get_image_and_save(client, task_id, topic, model_name, save_path)
                else:
                    logger.info(f"Image generation task {task_id} submitted. No save path specified.")
            else:
                logger.error("Failed to submit image generation task.")

# --- Example Usage ---
async def main_example():
    # Create an instance of the ImageClient
    image_client = ImageClient()

    logger.info("--- Drawing a Stable Diffusion 1.5 image with default LoRA ---")
    await image_client.draw_image(
        model_name="sd15",
        prompt="A majestic dragon flying over a medieval castle, highly detailed, fantasy art",
        save_path="./generated_images/dragon_castle.png"
    )

    logger.info("--- Drawing a Flux image without saving and custom LoRA ---")
    await image_client.draw_image(
        model_name="flux",
        prompt="A vibrant abstract painting with swirling colors and geometric shapes, modern art",
        loras=[{"name": "测试卡通动画又红又专", "weight": 0.9}] # Explicitly providing a LoRA
    )

    logger.info("--- Drawing another Flux image with a different save path and no custom LoRA (uses random default) ---")
    await image_client.draw_image(
        model_name="flux",
        prompt="A serene Japanese garden with cherry blossoms and a koi pond, peaceful atmosphere",
        save_path="./generated_images/japanese_garden.jpg" 
    )

    logger.info("--- Drawing an SD15 image with no LoRA (overriding default) ---")
    await image_client.draw_image(
        model_name="sd15",
        prompt="A photorealistic portrait of an old man with a beard, studio lighting",
        save_path="./generated_images/old_man.png",
        loras=[] # Explicitly providing an empty list to use no LoRAs
    )

if __name__ == "__main__":
    # Create the directory for generated images if it doesn't exist
    os.makedirs("./generated_images", exist_ok=True)
    asyncio.run(main_example())
