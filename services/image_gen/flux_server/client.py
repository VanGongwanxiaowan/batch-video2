"""Flux图像生成客户端

提供与Flux图像生成服务交互的客户端功能。
"""
import io
import sys
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.exceptions import ServiceException, ServiceUnavailableException
from core.logging_config import setup_logging

from .image_generation_config import ImageGenerationConfig, ImageGenerationResult

# 配置日志记录器
logger = setup_logging("image_gen.flux_server.client", log_to_file=False)

# Define the API endpoint URL
API_URL = "http://127.0.0.1:8015/generate_image/"  # Assuming the server runs locally on port 8000


def generate_image(
    prompt: str,
    num_inference_steps: int = 30,
    width: int = 1360,
    height: int = 768,
    lora_name: str = "",
    lora_step: int = 120,
) -> Optional[Image.Image]:
    """
    发送请求到FastAPI服务器生成图像（向后兼容接口）。
    
    此函数保留用于向后兼容，新代码应使用 `generate_image_with_config`。
    
    Args:
        prompt: 图像生成提示词
        num_inference_steps: 推理步数，默认30
        width: 图像宽度，默认1360
        height: 图像高度，默认768
        lora_name: LoRA模型名称（可选），默认空字符串
        lora_step: LoRA步数，默认120
        
    Returns:
        PIL Image对象（成功时），否则返回None
        
    Note:
        此函数将在未来版本中废弃，建议使用 `generate_image_with_config`
    """
    config = ImageGenerationConfig(
        prompt=prompt,
        num_inference_steps=num_inference_steps,
        width=width,
        height=height,
        lora_name=lora_name,
        lora_step=lora_step,
    )
    result = generate_image_with_config(config)
    return result.image if result.success else None


def generate_image_with_config(config: ImageGenerationConfig) -> ImageGenerationResult:
    """
    使用配置对象生成图像（推荐使用）。
    
    此函数使用配置数据类封装参数，提供更好的类型安全和可维护性。
    
    Args:
        config: 图像生成配置对象
        
    Returns:
        ImageGenerationResult: 包含生成结果的对象
        
    Raises:
        ValueError: 如果配置参数无效
        ServiceUnavailableException: 如果服务不可用
        ServiceException: 如果生成失败
    """
    # 验证配置
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"[generate_image_with_config] 配置验证失败: {e}")
        return ImageGenerationResult.error_result(f"配置无效: {e}")
    
    # 构建请求负载
    payload = {
        "prompt": config.prompt,
        "num_inference_steps": config.num_inference_steps,
        "width": config.width,
        "height": config.height,
    }
    
    # 如果提供了LoRA，添加到负载中
    if config.lora_name:
        payload["lora_name"] = config.lora_name
        payload["lora_step"] = config.lora_step
    
    logger.debug(f"[generate_image_with_config] 发送请求 payload={payload}")
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        
        if response.status_code == 200:
            return _process_successful_response(response)
        else:
            return _process_error_response(response)
            
    except requests.exceptions.Timeout as e:
        logger.error(f"[generate_image_with_config] 请求超时: {e}", exc_info=True)
        return ImageGenerationResult.error_result(f"请求超时: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"[generate_image_with_config] 连接错误: {e}", exc_info=True)
        raise ServiceUnavailableException("flux_server", f"无法连接到图像生成服务: {e}") from e
    except requests.exceptions.RequestException as e:
        logger.error(f"[generate_image_with_config] 请求失败: {e}", exc_info=True)
        raise ServiceException(f"图像生成请求失败: {e}") from e


def _process_successful_response(response: requests.Response) -> ImageGenerationResult:
    """处理成功的HTTP响应
    
    Args:
        response: HTTP响应对象
        
    Returns:
        ImageGenerationResult: 包含图像的结果对象
    """
    try:
        image = Image.open(io.BytesIO(response.content))
        logger.info("[generate_image_with_config] 图像生成成功")
        return ImageGenerationResult.success_result(image)
    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except (OSError, IOError, ValueError) as e:
        # 图像处理错误（文件IO错误、格式错误等）
        error_msg = f"图像处理错误: {e}"
        logger.error(f"[generate_image_with_config] {error_msg}", exc_info=True)
        return ImageGenerationResult.error_result(error_msg)
    except Exception as e:
        # 其他未预期的异常
        error_msg = f"处理图像响应时发生未知错误: {e}"
        logger.exception(f"[generate_image_with_config] {error_msg}")
        return ImageGenerationResult.error_result(error_msg)


def _process_error_response(response: requests.Response) -> ImageGenerationResult:
    """处理错误的HTTP响应
    
    Args:
        response: HTTP响应对象
        
    Returns:
        ImageGenerationResult: 包含错误信息的结果对象
    """
    status_code = response.status_code
    logger.error(f"[generate_image_with_config] 图像生成失败，状态码: {status_code}")
    
    try:
        error_details = response.json()
        error_msg = error_details.get('error', 'No error details provided.')
        logger.error(f"[generate_image_with_config] 错误详情: {error_msg}")
        return ImageGenerationResult.error_result(f"图像生成失败 (状态码 {status_code}): {error_msg}")
    except requests.exceptions.JSONDecodeError:
        logger.error("[generate_image_with_config] 无法解析错误响应为JSON")
        return ImageGenerationResult.error_result(f"图像生成失败 (状态码 {status_code}): 无法解析错误响应")


if __name__ == "__main__":
    # Example usage:
    # Make sure the FastAPI server (main.py) is running before running this client.

    # Example 1: Generate image with a simple prompt
    logger.info("--- Example 1: Simple Prompt ---")
    image1 = generate_image("a photo of an astronaut riding a horse on the moon", num_inference_steps=20, width=1024, height=1024)
    if image1:
        image1.save("astronaut_horse_moon.png")
        logger.info("Saved image to astronaut_horse_moon.png")
    logger.info("-" * 20)

    # Example 2: Generate image with a prompt and LoRA (replace with actual LoRA name if available)
    # print("--- Example 2: Prompt with LoRA ---")
    # # Replace 'your_lora_name' with the actual name of a LoRA file you have
    # # Make sure the LoRA file is in the directory specified by LORAS_BASE_PATH in flux.py
    # image2 = generate_image("a photo of a cat", lora_name="your_lora_name", lora_step=100)
    # if image2:
    #     image2.save("cat_with_lora.png")
    #     print("Saved image to cat_with_lora.png")
    # print("-" * 20)

    # Example 3: Generate image with a prompt and specifying device_id (if you have multiple GPUs)
    # print("--- Example 3: Prompt with Device ID ---")
    # # Replace '1' with the ID of your desired CUDA device
    # if image3:
    #     image3.save("futuristic_city_gpu1.png")
    #     print("Saved image to futuristic_city_gpu1.png")
    # print("-" * 20)
