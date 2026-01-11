"""文件管理器"""
import os
from pathlib import Path
from typing import List, Optional

from core.config.paths import PathManager
from core.logging_config import setup_logging

logger = setup_logging("worker.file_manager")


class FileManager:
    """文件管理器，统一管理文件路径和目录创建"""
    
    def __init__(self, path_manager: Optional[PathManager] = None) -> None:
        """
        初始化文件管理器
        
        Args:
            path_manager: 路径管理器，如果为None则使用默认的
        """
        from config import path_manager as default_path_manager
        self.path_manager = path_manager or default_path_manager
    
    def get_job_directory(self, job_id: int, user_id: str, title: str) -> Path:
        """
        获取任务目录
        
        Args:
            job_id: 任务ID
            user_id: 用户ID
            title: 标题
            
        Returns:
            任务目录路径
        """
        # 清理标题和用户ID
        title = title.replace(" ", "_").replace("+", "_")
        user_id = user_id.replace("-", "")
        
        if user_id:
            job_dir = self.path_manager.worker_assets_dir / user_id / title
        else:
            job_dir = self.path_manager.worker_assets_dir / title
        
        return job_dir.resolve()
    
    def ensure_directory(self, path: Path) -> Path:
        """
        确保目录存在
        
        Args:
            path: 目录路径
            
        Returns:
            目录路径
        """
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_file_path(self, base_dir: Path, filename: str) -> Path:
        """
        获取文件路径
        
        Args:
            base_dir: 基础目录
            filename: 文件名
            
        Returns:
            文件路径
        """
        return base_dir / filename
    
    def ensure_assets_path(self) -> None:
        """确保资源目录存在"""
        self.ensure_directory(self.path_manager.worker_assets_dir)
    
    def split_string_by_punctuation(self, text: str, min_length: int = 15) -> List[str]:
        """
        按标点符号分割文本
        
        Args:
            text: 原始文本
            min_length: 最小长度（CJK字符算2个单位）
            
        Returns:
            分割后的文本列表
        """
        import re
        
        def cjk_aware_len(txt: str) -> int:
            """计算文本长度，CJK字符算2个单位"""
            length = 0
            for char in txt:
                if (
                    "\u4e00" <= char <= "\u9fff"
                    or "\u3040" <= char <= "\u30ff"
                    or "\uac00" <= char <= "\ud7af"
                ):
                    length += 2
                else:
                    length += 1
            return length
        
        # 按标点符号分割
        pattern = r"([!·，。！？；,.!?;、\-—–—])"
        parts = re.split(pattern, text)
        
        cleaned_parts = [
            part.strip() for part in parts if part.strip() or re.match(pattern, part)
        ]
        
        processed_segments = []
        current_segment = ""
        
        for i, part in enumerate(cleaned_parts):
            if re.match(pattern, part):
                if current_segment:
                    current_segment += part
            else:
                if current_segment:
                    current_segment += part
                else:
                    current_segment = part
            
            if i + 1 < len(cleaned_parts) and not re.match(pattern, cleaned_parts[i + 1]):
                if cjk_aware_len(current_segment) >= min_length:
                    processed_segments.append(current_segment)
                    current_segment = ""
            elif i == len(cleaned_parts) - 1:
                if processed_segments and cjk_aware_len(current_segment) < min_length:
                    processed_segments[-1] += current_segment
                else:
                    processed_segments.append(current_segment)
        
        # 清理结果
        results = []
        for part in processed_segments:
            txt = part.strip().replace("\n", "")
            txt = re.sub(r"^[，。！？；,.!?;、\-—–—]+", "", txt)
            txt = re.sub(r"[，。！？；,.!?;、\-—–—]+$", "", txt)
            txt = txt.strip("”")
            results.append(txt)
        
        new_results = []
        for part in results:
            txt = part.strip(",").strip("。").strip("，").strip("、")
            txt = txt.strip("”").strip(":").strip(".").strip("!")
            txt = txt.replace("\n", "")
            if txt:
                new_results.append(txt)
        
        return new_results

