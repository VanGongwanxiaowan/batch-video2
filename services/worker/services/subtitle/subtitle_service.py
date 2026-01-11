"""字幕处理服务"""
import os
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pysrt
from opencc import OpenCC

from core.logging_config import setup_logging
from services.base import BaseService

logger = setup_logging("worker.subtitle")


# 方块字语言列表
SQUARE_WORDS_LIST = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "ko-KR-SunHiNeural",
    "ja-JP-NanamiNeural",
    "zh-TW-HsiaoChenNeural",
    "zh-HK-HiuGaaiNeural",
    "th-TH-PremwadeeNeural",
    "lo-LA-KeomanyNeural",
    "my-MM-NilarNeural",
]


class SubtitleService(BaseService):
    """字幕处理服务"""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config, logger)
    
    def get_char_display_width(self, char: str) -> int:
        """
        根据字符的东亚宽度属性确定显示宽度
        
        Args:
            char: 单个字符
            
        Returns:
            字符宽度（1或2）
        """
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in ("F", "W", "A"):  # Fullwidth, Wide, Ambiguous
            return 2
        return 1  # Narrow, Halfwidth, Neutral
    
    def add_line_breaks(self, text: str, max_chars: int = 25) -> str:
        """
        字幕换行，根据字符显示宽度进行换行，避免截断中文
        
        Args:
            text: 原始文本
            max_chars: 最大字符数
            
        Returns:
            换行后的文本
        """
        text = text.replace("\n", "")
        lines = []
        current_line = []
        current_width = 0

        for char in text:
            char_width = self.get_char_display_width(char)
            if current_width + char_width > max_chars:
                lines.append("".join(current_line))
                current_line = [char]
                current_width = char_width
            else:
                current_line.append(char)
                current_width += char_width

        if current_line:
            lines.append("".join(current_line))

        return "\n".join(lines)
    
    def add_square_line_breaks(self, text: str, max_chars: int = 13) -> str:
        """
        方块字语言换行（中文、日语、韩文等）
        
        Args:
            text: 原始文本
            max_chars: 最大字符数
            
        Returns:
            换行后的文本
        """
        text = text.replace("\n", "")
        return "\n".join([text[i : i + max_chars] for i in range(0, len(text), max_chars)])
    
    def add_none_square_line_breaks(self, text: str, max_chars: int = 24) -> str:
        """
        非方块字语言换行（英文等）
        
        Args:
            text: 原始文本
            max_chars: 最大字符数
            
        Returns:
            换行后的文本
        """
        words = text.split(" ")
        text = ""
        lines = []
        for word in words:
            if len(text) + len(word) < int(max_chars):
                text += word + " "
            else:
                lines.append(text)
                text = word + " "
        if len(text) > 0:
            lines.append(text)
        return "\n".join(lines)
    
    def process_srt_break(
        self, 
        srt_file_path: str, 
        square: bool = True, 
        is_horizontal: bool = True
    ) -> str:
        """
        处理字幕文件，进行换行等处理
        
        Args:
            srt_file_path: 字幕文件路径
            square: 是否为方块字语言
            is_horizontal: 是否为横向布局
            
        Returns:
            处理后的字幕文件路径
        """
        subs = pysrt.open(srt_file_path, encoding="utf-8")
        new_subs = pysrt.SubRipFile()
        index = 0
        
        for sub in subs:
            if square:
                max_chars = 13
                if not is_horizontal:
                    max_chars = 8
                if len(sub.text) > max_chars * 2:
                    # 将字幕按照字数分成2份，时间按照字数平均分配
                    text = sub.text.replace("\n", "")
                    text1 = text[: int(max_chars * 1.6)]
                    text2 = text[int(max_chars * 1.6) :]
                    text1 = self.add_square_line_breaks(text1, max_chars)
                    text2 = self.add_square_line_breaks(text2, max_chars)
                    
                    if text1.strip():
                        sub1 = pysrt.SubRipItem(
                            index=index,
                            start=sub.start,
                            end=sub.start + int((len(text1) / len(text)) * sub.duration.ordinal),
                            text=text1,
                        )
                        new_subs.append(sub1)
                        index += 1
                    if text2.strip():
                        sub2 = pysrt.SubRipItem(
                            index=index,
                            start=sub.start + int((len(text1) / len(text)) * sub.duration.ordinal),
                            end=sub.end,
                            text=text2,
                        )
                        new_subs.append(sub2)
                        index += 1
                else:
                    sub.text = self.add_square_line_breaks(sub.text, max_chars)
                    sub.index = index
                    new_subs.append(sub)
                    index += 1
            else:
                max_chars = 24
                if not is_horizontal:
                    max_chars = 16
                words = sub.text.split(" ")
                if len(sub.text) > max_chars:
                    text = sub.text.replace("\n", " ")
                    text1 = ""
                    text2 = ""
                    for word in words:
                        if len(text1) + len(word) < int(max_chars * 1.6):
                            text1 += word + " "
                        else:
                            text2 += word + " "

                    text1 = self.add_none_square_line_breaks(text1, max_chars)
                    text2 = self.add_none_square_line_breaks(text2, max_chars)

                    if text1.strip():
                        sub1 = pysrt.SubRipItem(
                            index=index,
                            start=sub.start,
                            end=sub.start + int((len(text1) / len(text)) * sub.duration.ordinal),
                            text=text1,
                        )
                        new_subs.append(sub1)
                        index += 1
                    if text2.strip():
                        sub2 = pysrt.SubRipItem(
                            index=index,
                            start=sub.start + int((len(text1) / len(text)) * sub.duration.ordinal),
                            end=sub.end,
                            text=text2,
                        )
                        new_subs.append(sub2)
                        index += 1
                else:
                    sub.text = self.add_none_square_line_breaks(sub.text, max_chars)
                    sub.index = index
                    new_subs.append(sub)
                    index += 1
        
        new_subs.save(srt_file_path, encoding="utf-8")
        return srt_file_path
    
    def convert_to_traditional(self, srt_file_path: str) -> str:
        """
        将字幕转换为繁体中文
        
        Args:
            srt_file_path: 字幕文件路径
            
        Returns:
            转换后的字幕文件路径
        """
        cc = OpenCC("s2tw")  # Simplified Chinese to Traditional Chinese
        subs = pysrt.open(srt_file_path, encoding="utf-8")
        for sub in subs:
            sub.text = cc.convert(sub.text)
        subs.save(srt_file_path, encoding="utf-8")
        return srt_file_path
    
    def is_square_language(self, language: str) -> bool:
        """
        判断是否为方块字语言
        
        Args:
            language: 语言代码
            
        Returns:
            是否为方块字语言
        """
        return language in SQUARE_WORDS_LIST
    
    async def process(self, data: dict) -> dict:
        """
        处理字幕数据
        
        Args:
            data: 包含字幕文件路径和处理选项的字典
            
        Returns:
            处理结果字典
        """
        srt_file_path = data.get("srt_file_path")
        square = data.get("square", True)
        is_horizontal = data.get("is_horizontal", True)
        convert_traditional = data.get("convert_traditional", False)
        
        if not srt_file_path or not os.path.exists(srt_file_path):
            return {"success": False, "error": "字幕文件不存在"}
        
        try:
            # 处理字幕换行
            self.process_srt_break(srt_file_path, square, is_horizontal)
            
            # 如果需要转换为繁体中文
            if convert_traditional:
                self.convert_to_traditional(srt_file_path)
            
            return {
                "success": True,
                "srt_file_path": srt_file_path
            }
        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except Exception as e:
            # 其他异常（字幕生成错误等）
            return self.handle_error(e)

