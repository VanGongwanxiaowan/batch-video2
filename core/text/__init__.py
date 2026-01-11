"""
文本处理核心模块

提供文本处理的基础功能，包括文本分割、清洗等功能。
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class TextChunk:
    """文本块数据类"""
    index: int
    text: str
    word_count: int
    metadata: Optional[Dict[str, Any]] = None

class TextSplitError(Exception):
    """文本分割异常基类"""
    pass

class InvalidSplitterConfigError(TextSplitError):
    """无效的分割器配置异常"""
    pass

class SplitterNotInitializedError(TextSplitError):
    """分割器未正确初始化异常"""
    pass
