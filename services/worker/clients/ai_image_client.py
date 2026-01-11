import asyncio
import json
import os
import random
import sys
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
import requests

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.clients.ai_image_client", log_to_file=False)

def get_prefix(loras: List[Dict[str, Any]] = None, prompt: str = "") -> str:
    """根据LoRA配置生成提示词前缀
    
    Args:
        loras: LoRA配置列表
        prompt: 原始提示词
        
    Returns:
        str: 生成的提示词前缀
    """
    if loras is None:
        loras = []
    res = ""
    for image_lora_dict in loras:
        image_lora = image_lora_dict.get("name", "")
        if not image_lora:
            continue

        if "水彩" in image_lora:
            res += "watercalor,"
        if "黑白线稿" in image_lora:
            res += "heibaixiaogao, a black-and-white line drawing depicting,"
        if "抽象蜡笔" in image_lora:
            res += "in the style of isb, a vibrant, colorful drawing created using bold, expressive strokes."
        if "可爱卡通3D" in image_lora:
            res += "cute,"
        if "古风" in image_lora and "chinese" not in prompt.lower() and "china" not in prompt.lower() and "ancient" not in prompt.lower():
            res += "Ancient China,"
        if "推文韩漫" in image_lora:
            res += "ddong,"
        if "国潮" in image_lora or "传统山水" in image_lora:
            res += "Chinese painting,"
        if "浮世绘" in image_lora:
            res += "Ukiyo-e style,"
        if "玄幻古风" in image_lora:
            res += "Chinese mythology,"
        if "古风黑白水墨画风插画" in image_lora:
            res += "Ancient style, black and white, ink wash, brushstrokes,"
        if "恐怖悬疑" == image_lora:
            res += "xy,"
        if "恐怖人物场景小说推文海报对比色彩" == image_lora:
            res += "kongbu,dark fairy,"
        if "恐怖游戏画风" == image_lora:
            res += "kongbu,dark fairy,animate style,"
        if "恐怖悬疑小说推文恐怖漫画" in image_lora:
            res += "anxilie,Comic style, with intricate black-and-white textures and high-contrast lighting,"
        if "鸟山明画风" in image_lora:
            res += "animate style,"
        if "异色迷幻" in image_lora:
            res += "Dark style animation,"
        if "血源诅咒" in image_lora:
            res += "thedoll, dark style animation,"
        if "赛博朋克科幻风格" == image_lora:
            res += "FRESH IDEAS Cyberpunk,"
        if "赛博朋克公民" in image_lora:
            res += "Cyberpunk_Citizen,"
        if "桃花言情漫画绘画风格漫画" == image_lora:
            res += "tata,Chinese costume anime,"
        if "古风超绝氛围感cp风" == image_lora:
            res += "couple," # "couple,1girl and 1boy,"
        if "现代都市言情国漫风" == image_lora:
            res += "yanqing,"
        if "替嫁王妃" == image_lora:
            res += "tijiawangfei,chinese ancient,"
        if "太子妃升职记" in image_lora:
            res += "taizifei, chinese ancient,"
        if "顾太太" in image_lora:
            res += "gutaitai,"
        if "又红又专" in image_lora:
            res += "maoxuan,"
        if len(image_lora.split("-")) == 2:
            res += image_lora.split("-")[1] + ","
    res = res.replace("_", "-")
    return res

class ImageGenerationTopic(str, Enum):
    # sdxl_tasks,sd15_tasks,flux_tasks
    FLUX = "flux_tasks"
    SD15 = "sd15_tasks"
    SDXL = "sdxl_tasks"

# Base URL of your FastAPI service
BASE_URL = "http://localhost:8000"


def generate_ai_image(
    topic: str, 
    model_name: str, 
    loras: Optional[List[Dict[str, Any]]] = None, 
    prompt: str = "", 
    width: int = 1360, 
    height: int = 768
) -> Dict[str, Any]:
    """Generates sample image generation request data.
    
    Args:
        topic: 主题
        model_name: 模型名称
        loras: LoRA配置列表
        prompt: 提示词
        width: 图片宽度
        height: 图片高度
        
    Returns:
        Dict[str, Any]: 图像生成请求数据
    """
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
        "width": width,
        "height": height,
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

async def submit_image_generation_task(
    client: httpx.AsyncClient, 
    topic: str, 
    model_name: str, 
    data: Dict[str, Any]
) -> Optional[Tuple[Optional[str], Optional[str], Optional[str]]]:
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

def submit_image_generation_tasks_sync(
    topic: str, 
    model_name: str, 
    data: Dict[str, Any]
) -> Optional[Tuple[Optional[str], Optional[str], Optional[str]]]:
    try:
        response = requests.post(f"{BASE_URL}/generate_image", json=data)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Task submitted: {result}")
        return result.get("task_id"), topic, model_name
    except requests.HTTPError as e:
        logger.error(f"Error submitting task: {e.response.status_code} - {e.response.text}")
        return None, None, None
    except requests.RequestException as e:
        logger.exception(f"Network error submitting task: {e}")
        return None, None, None

async def check_task_status(
    client: httpx.AsyncClient, 
    task_id: str
) -> Optional[Dict[str, Any]]:
    """Checks the status of an image generation task.
    
    Args:
        client: HTTP异步客户端
        task_id: 任务ID
        
    Returns:
        Optional[Dict[str, Any]]: 任务状态字典，失败返回None
    """
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


def check_task_status_sync(task_id: str) -> Optional[Dict[str, Any]]:
    """Checks the status of an image generation task.
    
    Args:
        task_id: 任务ID
        
    Returns:
        Optional[Dict[str, Any]]: 任务状态字典，失败返回None
    """
    logger.debug(f"Checking status for task: {task_id}...")
    try:
        response = requests.get(f"{BASE_URL}/check_status/{task_id}")
        response.raise_for_status()
        result = response.json()
        logger.debug(f"Task status for {task_id}: {result}")
        return result
    except requests.HTTPError as e:
        logger.error(f"Error checking status: {e.response.status_code} - {e.response.text}")
        return None
    except requests.RequestException as e:
        logger.exception(f"Network error checking status: {e}")
        return None
    
async def get_image_and_save(
    client: httpx.AsyncClient, 
    task_id: str, 
    topic: str, 
    model_name: str, 
    filepath: str
) -> None:
   """Continuously calls get_image API and saves the image if successful.
   
   Args:
       client: HTTP异步客户端
       task_id: 任务ID
       topic: 主题
       model_name: 模型名称
       filepath: 保存文件路径
   """
   while True:
       try:
           response = await client.get(f"{BASE_URL}/get_image/{task_id}")
           response.raise_for_status()

           with open(filepath, "wb") as f:
               f.write(response.content)
           logger.info(f"Successfully retrieved and saved image for task {task_id}.")
           logger.info(f"Task ID: {task_id}, Topic: {topic}, Model: {model_name}, File Path: {filepath}")
           break # Exit loop if image is successfully retrieved
       except httpx.HTTPStatusError as e:
           if e.response.status_code == 400 and "not completed" in e.response.text:
               await asyncio.sleep(1)
           elif e.response.status_code == 404 and "not found" in e.response.text:
               await asyncio.sleep(1)
           else:
               logger.error(f"Error retrieving image for task {task_id}: {e.response.status_code} - {e.response.text}")
               break # Exit on other errors
       except httpx.RequestError as e:
           logger.debug(f"Network error retrieving image for task {task_id}, retrying...")
           await asyncio.sleep(1)
        
def get_image_and_save_sync(
    task_id: str, 
    topic: str, 
    model_name: str, 
    filepath: str
) -> Optional[str]:
    """同步获取图像并保存
    
    Args:
        task_id: 任务ID
        topic: 主题
        model_name: 模型名称
        filepath: 保存文件路径
        
    Returns:
        Optional[str]: 成功返回文件路径，失败返回None
    """
    for _ in range(600):
        try:
           response = requests.get(f"{BASE_URL}/get_image/{task_id}")
           response.raise_for_status()
           with open(filepath, "wb") as f:
               f.write(response.content)
               logger.info(f"Successfully retrieved and saved image for task {task_id}.")
               logger.info(f"Task ID: {task_id}, Topic: {topic}, Model: {model_name}, File Path: {filepath}")
               break # Exit loop if image is successfully retrieved
               
        except requests.HTTPError as e:
            if e.response.status_code == 400 and "not completed" in e.response.text:
                time.sleep(1)
            elif e.response.status_code == 404 and "not found" in e.response.text:
                time.sleep(1)
            else:
                logger.error(f"Error retrieving image for task {task_id}: {e.response.status_code} - {e.response.text}")
                break
        except requests.RequestException as e:
            logger.debug(f"Network error retrieving image for task {task_id}, retrying...")
            time.sleep(1)

async def get_image(
    client: httpx.AsyncClient, 
    task_id: str
) -> Optional[bytes]:
   """Continuously calls get_image API and returns the image content if successful.
   
   Args:
       client: HTTP异步客户端
       task_id: 任务ID
       
   Returns:
       Optional[bytes]: 图像内容，失败返回None
   """
   for _ in range(600):
        try:
           response = await client.get(f"{BASE_URL}/get_image/{task_id}")
           response.raise_for_status()
           return response.content
        except httpx.HTTPStatusError as e:
           if e.response.status_code == 400 and "not completed" in e.response.text:
               await asyncio.sleep(1)
           elif e.response.status_code == 404 and "not found" in e.response.text:
               await asyncio.sleep(1)
           else:
               break # Exit on other errors
