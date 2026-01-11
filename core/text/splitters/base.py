"""
文本分割器基类模块

定义所有文本分割器的基类接口。
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from ..text import TextChunk, TextSplitError

class BaseTextSplitter(ABC):
    """
    文本分割器抽象基类
    
    所有具体的文本分割器都应该继承此类并实现 split 方法。
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        **kwargs
    ):
        """
        初始化文本分割器
        
        Args:
            chunk_size: 每个文本块的最大长度
            chunk_overlap: 块之间的重叠长度
            **kwargs: 其他参数
            
        Raises:
            InvalidSplitterConfigError: 如果配置无效
        """
        if chunk_overlap >= chunk_size:
            raise TextSplitError(
                f"块重叠({chunk_overlap})不能大于或等于块大小({chunk_size})"
            )
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._validate_config()
    
    def _validate_config(self) -> None:
        """验证分割器配置"""
        if self.chunk_size <= 0:
            raise TextSplitError(f"块大小必须大于0，当前为{self.chunk_size}")
        if self.chunk_overlap < 0:
            raise TextSplitError(f"块重叠不能为负数，当前为{self.chunk_overlap}")
    
    @abstractmethod
    def split(self, text: str) -> List[TextChunk]:
        """
        将文本分割成多个块
        
        Args:
            text: 要分割的文本
            
        Returns:
            List[TextChunk]: 分割后的文本块列表
            
        Raises:
            TextSplitError: 如果分割过程中发生错误
        """
        pass
    
    def _create_chunk(
        self, 
        text: str, 
        index: int, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> TextChunk:
        """
        创建文本块对象
        
        Args:
            text: 块文本
            index: 块索引
            metadata: 元数据
            
        Returns:
            TextChunk: 文本块对象
        """
        return TextChunk(
            index=index,
            text=text,
            word_count=len(text),
            metadata=metadata or {}
        )
