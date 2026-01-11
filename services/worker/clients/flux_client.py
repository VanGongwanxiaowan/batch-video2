import io
import sys
from pathlib import Path
from typing import Optional

from PIL import Image

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging
# 使用共享 HTTP Session
from core.utils.http_session import get_http_session

# 配置日志
logger = setup_logging("worker.clients.flux_client", log_to_file=False)

# Define the API endpoint URL
API_URL = "http://127.0.0.1:8015/generate_image/" # Assuming the server runs locally on port 8000

# 获取共享 Session（使用连接池优化性能）
_http_session = get_http_session()

def generate_image(
    prompt: str,
    num_inference_steps: int = 30,
    width: int = 1360,
    height: int = 768,
    lora_name: str = "",
    lora_step: int = 120
) -> Optional[Image.Image]:
    """
    Sends a request to the FastAPI server to generate an image.

    使用共享 HTTP Session，自动复用 TCP 连接。

    Args:
        prompt: The text prompt for image generation.
        num_inference_steps: The number of inference steps to use.
        width: The width of the generated image.
        height: The height of the generated image.
        lora_name: Optional name of the LoRA model to use.
        lora_step: Optional step value for the LoRA model.

    Returns:
        Optional[Image.Image]: The PIL Image object if successful, otherwise None.
    """
    payload = {
        "prompt": prompt,
        "num_inference_steps": num_inference_steps,
        "width": width,
        "height": height,
    }

    if lora_name:
        payload["loras"] = [{
            "name": lora_name,
            "weight": lora_step / 100,
        }]
    logger.debug(f"Sending request with payload: {payload}")

    try:
        # 使用共享 Session（连接池自动复用 + 自动重试）
        response = _http_session.post(API_URL, json=payload)

        if response.status_code == 200:
            # Assuming the response content is the image bytes
            try:
                image = Image.open(io.BytesIO(response.content))
                logger.info("Image generated successfully.")
                return image
            except (SystemExit, KeyboardInterrupt):
                # 系统退出异常，不捕获，直接抛出
                raise
            except (OSError, IOError, ValueError) as img_e:
                # 图像处理错误（文件IO错误、格式错误等）
                logger.error(f"[generate_image] 图像处理失败: {img_e}", exc_info=True)
                return None
            except Exception as img_e:
                # 其他未预期的异常
                logger.exception(f"[generate_image] 处理图像响应时发生未知异常: {img_e}")
                return None
        else:
            logger.error(f"Error generating image. Status code: {response.status_code}")
            try:
                error_details = response.json()
                logger.error(f"Error details: {error_details.get('error', 'No error details provided.')}")
            except Exception:
                logger.error("Could not decode error response as JSON.")
            return None

    except (SystemExit, KeyboardInterrupt):
        # 系统退出异常，不捕获，直接抛出
        raise
    except Exception as e:
        # 网络请求错误（Session 已配置自动重试）
        logger.error(f"[generate_image] 请求失败: {e}", exc_info=True)
        return None

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