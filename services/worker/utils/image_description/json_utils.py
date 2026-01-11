"""JSON处理工具模块

提供JSON文本修复和验证功能。
"""
import json
from typing import Optional

from json_repair import repair_json

from core.logging_config import setup_logging

logger = setup_logging("worker.utils.image_description.json_utils")


def clean_json_text(text: str) -> str:
    """清理JSON文本，移除代码块标记和多余空白。
    
    Args:
        text: 原始文本，可能包含代码块标记（```）和多余空白
        
    Returns:
        清理后的文本
    """
    # 移除代码块标记
    text = text.replace("```", "").strip()
    text = text.replace("JSON", "").strip()
    text = text.replace("json", "").strip()
    
    # 提取JSON部分（从第一个 { 到最后一个 }）
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return text
    
    return text[start_idx:end_idx + 1]


def fix_and_validate_json(text: str) -> str:
    """修复并验证JSON格式文本。
    
    此函数会：
    1. 清理文本（移除代码块标记等）
    2. 使用json_repair修复JSON格式
    3. 验证JSON是否有效
    
    Args:
        text: 原始文本，可能格式不正确
        
    Returns:
        修复后的JSON字符串（即使验证失败也会返回）
        
    Raises:
        不会抛出异常，验证失败时返回原文本并记录警告
    """
    cleaned_text = clean_json_text(text)
    repaired_text = repair_json(cleaned_text)
    
    try:
        # 验证JSON是否有效
        json.loads(repaired_text)
        return repaired_text
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"JSON格式验证失败: {e}")
        return repaired_text


def parse_json_safely(text: str) -> Optional[dict]:
    """安全地解析JSON文本。
    
    Args:
        text: JSON格式的文本
        
    Returns:
        解析后的字典，如果解析失败则返回None
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"JSON解析失败: {e}")
        return None

