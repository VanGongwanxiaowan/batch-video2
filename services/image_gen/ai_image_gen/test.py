import asyncio
import json
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
logger = setup_logging("image_gen.ai_image_gen.test", log_to_file=False)

# Base URL of your FastAPI service
BASE_URL = "http://localhost:8000"

def generate_image_request_data(topic: str, model_name: str):
    """Generates sample image generation request data."""
    task_id = str(uuid.uuid4())
    
    # Default values
    prompt = f"A futuristic city at sunset, highly detailed, {task_id}"
    negative_prompt = "blurry, low quality"
    image_params = {"width": 512, "height": 512, "steps": 10, "cfg_scale": 2.0, "seed": -1, "batch_size": 1}
    loras = []
    
    request_data = {
        "user_id": "test_user_" + str(random.randint(1, 100)),
        "topic": topic, # Add topic to the request data
        "model_name": model_name,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "image_params": image_params,
        "loras": loras,
    }

    if model_name == "sd15":
        prompt = f"A fantasy landscape, {task_id}"
        negative_prompt = "ugly, deformed"
        image_params = {"width": 512, "height": 512, "steps": 20, "cfg_scale": 7.0, "seed": -1, "batch_size": 1}
        loras = [{"name": "KoalaEngineV2a", "weight": 0.8}]
    elif model_name == "flux":
        prompt = "A cyberpunk street scene with neon lights and rain, intricate details"
        negative_prompt = "cartoon, anime, low resolution"
        image_params = {
            "width": 1024,
            "height": 1024,
            "steps": 5,
            "cfg_scale": 6.0,
            "seed": -1, # Random seed
            "batch_size": 1
        }
        lora_name = random.choice(["擦边北岸纯欲性感脸模黛雅.beiansafetensors", "古风漫画男主", "测试卡通动画又红又专"])
        loras = [
            {"name": lora_name, "weight": 0.8}
        ]

    return request_data

async def submit_image_generation_task(client: httpx.AsyncClient, topic: str, model_name: str):
    """Submits an image generation task to the API."""
    data = generate_image_request_data(topic, model_name)
    logger.info(f"Submitting task for topic: {topic}, model: {model_name} with prompt: {data['prompt'][:50]}...")
    try:
        response = await client.post(f"{BASE_URL}/generate_image", json=data)
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

async def check_task_status(client: httpx.AsyncClient, task_id: str):
    """Checks the status of an image generation task."""
    logger.debug(f"Checking status for task: {task_id}...")
    try:
        response = await client.get(f"{BASE_URL}/check_status/{task_id}")
        response.raise_for_status()
        result = response.json()
        logger.debug(f"Task status for {task_id}: {result}")
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Error checking status: {e.response.status_code} - {e.response.text}")
        return None
    except httpx.RequestError as e:
        logger.exception(f"Network error checking status: {e}")
        return None


async def get_image_and_save(client: httpx.AsyncClient, task_id: str, topic: str, model_name: str):
   """Continuously calls get_image API and saves the image if successful."""
   output_dir = "./tmp"
   os.makedirs(output_dir, exist_ok=True)
   while True:
       try:
           response = await client.get(f"{BASE_URL}/get_image/{task_id}")
           response.raise_for_status()
           
           # Determine file extension from content-type header or default to .png
           content_type = response.headers.get("content-type", "application/octet-stream")
           if "image/png" in content_type:
               file_extension = "png"
           elif "image/jpeg" in content_type:
               file_extension = "jpg"
           else:
               file_extension = "bin" # Default for unknown types

           image_filename = f"{task_id}.{file_extension}"
           image_path = os.path.join(output_dir, image_filename)

           with open(image_path, "wb") as f:
               f.write(response.content)
           
           logger.info(f"Successfully retrieved and saved image for task {task_id}.")
           logger.info(f"Task ID: {task_id}, Topic: {topic}, Model: {model_name}, File Path: {image_path}")
           break # Exit loop if image is successfully retrieved
       except httpx.HTTPStatusError as e:
           if e.response.status_code == 400 and "not completed" in e.response.text:
               await asyncio.sleep(1)
           elif e.response.status_code == 404 and "not found" in e.response.text:
               await asyncio.sleep(1)
           else:
               break # Exit on other errors
       except httpx.RequestError as e:
           await asyncio.sleep(1)

async def main():
   async with httpx.AsyncClient() as client:
        # Test image generation
        logger.info("--- Testing Image Generation ---")
        submitted_tasks_info = [] # Store (task_id, topic, model_name)

        # Test online_task with random model_name (sd15 or flux)
        for _ in range(15):
           task_id, topic, model_name = await submit_image_generation_task(client, "sd15_tasks", "sd15")
           if task_id:
               submitted_tasks_info.append((task_id, topic, model_name))
           await asyncio.sleep(0.1)

           task_id, topic, model_name = await submit_image_generation_task(client, "flux_tasks", "flux")
           if task_id:
               submitted_tasks_info.append((task_id, topic, model_name))
           await asyncio.sleep(0.1)

        for i in range(5):
           model_name_for_online = random.choice(["sd15", "flux"])
           task_id, topic, model_name = await submit_image_generation_task(client, "online_task", model_name_for_online)
           if task_id:
               submitted_tasks_info.append((task_id, topic, model_name))
           await asyncio.sleep(0.1) # Small delay

        # Continuously call get_image and save
        logger.info("--- Testing Image Retrieval and Saving ---")
        await asyncio.gather(*[get_image_and_save(client, task_id, topic, model_name) for task_id, topic, model_name in submitted_tasks_info])

if __name__ == "__main__":
   import os  # Import os for directory creation
   asyncio.run(main())