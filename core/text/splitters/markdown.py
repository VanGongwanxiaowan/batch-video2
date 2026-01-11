"""
Markdown文本分割器

提供基于Markdown语法的文本分割功能。
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass

from .base import BaseTextSplitter
from ..text import TextChunk, TextSplitError

@dataclass
class MarkdownHeader:
    """Markdown标题信息"""
    level: int
    text: str
    
class MarkdownSplitter(BaseTextSplitter):
    """
    Markdown文本分割器
    
    根据Markdown的标题结构来分割文档。
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        header_levels: Optional[List[int]] = None,
        **kwargs
    ):
        """
        初始化Markdown分割器
        
        Args:
            chunk_size: 每个文本块的最大长度
            chunk_overlap: 块之间的重叠长度
            header_levels: 用于分割的标题级别，例如[1, 2]表示一级和二级标题
            **kwargs: 其他参数
        """
        super().__init__(chunk_size, chunk_overlap, **kwargs)
        self.header_levels = header_levels or [1, 2]
        self._validate_header_levels()
    
    def _validate_header_levels(self) -> None:
        """验证标题级别配置"""
        if not self.header_levels:
            raise TextSplitError("至少需要指定一个标题级别用于分割")
        
        if not all(isinstance(level, int) and level > 0 for level in self.header_levels):
            raise TextSplitError("标题级别必须是正整数")
    
    def split(self, text: str) -> List[TextChunk]:
        """
        将Markdown文本分割成多个块
        
        Args:
            text: 要分割的Markdown文本
            
        Returns:
            List[TextChunk]: 分割后的文本块列表
            
        Raises:
            TextSplitError: 如果分割过程中发生错误
        """
        if not text.strip():
            return []
            
        try:
            chunks = []
            current_chunk = []
            current_headers = []
            
            for line in text.split('\n'):
                header = self._parse_header(line)
                if header and header.level in self.header_levels:
                    if current_chunk:
                        chunks.append((current_headers.copy(), '\n'.join(current_chunk)))
                        current_chunk = []
                    current_headers = [h for h in current_headers if h.level < header.level]
                    current_headers.append(header)
                
                current_chunk.append(line)
            
            # 添加最后一个块
            if current_chunk:
                chunks.append((current_headers, '\n'.join(current_chunk)))
            
            # 转换为TextChunk对象
            return [
                self._create_chunk(
                    text=chunk_text,
                    index=i,
                    metadata={
                        'headers': [{'level': h.level, 'text': h.text} for h in headers],
                        'chunk_type': 'markdown_section'
                    }
                )
                for i, (headers, chunk_text) in enumerate(chunks)
            ]
            
        except Exception as e:
            raise TextSplitError(f"Markdown分割失败: {str(e)}") from e
    
    def _parse_header(self, line: str) -> Optional[MarkdownHeader]:
        """
        解析Markdown标题行
        
        Args:
            line: 要解析的行
            
        Returns:
            Optional[MarkdownHeader]: 如果是标题行则返回标题信息，否则返回None
        """
        line = line.strip()
        
        # 匹配 # 开头的标题
        match = re.match(r'^(#{1,6})\s+(.*?)(?:\s+#*)?$', line)
        if match:
            level = len(match.group(1))
            return MarkdownHeader(level=level, text=match.group(2).strip())
        
        # 匹配下划线样式的标题
        match = re.match(r'^([^\n]+)\n[=]+$', line + '\n' + (line and '=' * len(line) or ''))
        if match:
            return MarkdownHeader(level=1, text=match.group(1).strip())
            
        match = re.match(r'^([^\n]+)\n[-]+$', line + '\n' + (line and '-' * len(line) or ''))
        if match:
            return MarkdownHeader(level=2, text=match.group(1).strip())
            
        return None
