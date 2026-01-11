"""
生成工具函数模块
提供视频生成过程中的工具函数
"""
import os
from typing import Dict

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.generation.generation_utils")


def calculate_points(assrtpath: str, content: str) -> Dict[str, float]:
    """
    计算点数
    
    Args:
        assrtpath: 资源路径
        content: 文本内容
        
    Returns:
        包含图片数、字数、点数的字典
    """
    files = os.listdir(assrtpath)
    image_count = len([f for f in files if f.endswith(".png")])
    words_count = len(content) / 1000
    points = round(image_count + words_count)
    
    return {
        "image": image_count,
        "words": words_count,
        "points": points
    }

