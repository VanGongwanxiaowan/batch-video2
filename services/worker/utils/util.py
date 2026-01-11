# 添加项目根目录到Python路径
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import oss2  # Import oss2 library
import requests

# import os # Import os for environment variables

_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging
from core.cache import cached

# 配置日志
logger = setup_logging("worker.utils.util", log_to_file=False)

def ocr_image(image_path: str) -> Optional[Dict[str, Any]]:
    """OCR图片识别
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        OCR识别结果的JSON数据，如果失败则返回None
    """
    from config import settings
    ocr_url_base = settings.OCR_SERVICE_URL

    url = f"{ocr_url_base}/ocr/"  # URL of the FastAPI service
    # 使用上下文管理器确保文件正确关闭
    with open(image_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get OCR result. Status Code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None


import sys
from pathlib import Path

from openai import OpenAI

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from config import settings


@cached(key_prefix="llm_chat", ttl=86400) # Cache for 24 hours
def chat_with_llm(prompt: str, model: str = 'deepseek-r1') -> str:
    api_key = settings.LLM_API_KEY
    api_base = settings.LLM_API_BASE
    
    if not api_key:
        raise ValueError("LLM_API_KEY环境变量未设置")
    
    client = OpenAI(api_key=api_key, base_url=api_base)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
        ],
        stream=False,
        max_tokens=200000
    )
    return response.choices[0].message.content

if __name__ == '__main__':
    # print(ocr_image('/path/to/your/image.png'))
    result = chat_with_llm('你好','gemini-2.5-flash')
    logger.info(f"LLM response: {result}")
