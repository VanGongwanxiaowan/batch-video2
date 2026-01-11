"""
字幕格式化工具模块
从 pipe_line.py 中提取的字幕处理相关函数
"""

import sys
from pathlib import Path
from typing import List

import pysrt

# 添加项目根目录到Python路径
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.logging_config import setup_logging

# 配置日志
logger = setup_logging("worker.utils.subtitle_formatter", log_to_file=False)


def add_line_breaks(traditional_text: str, max_chars: int = 25) -> str:
    """字幕换行，根据字符显示宽度进行换行，避免截断中文"""
    from .text_processor import get_char_display_width
    
    text = traditional_text.replace("\n", "")
    lines = []
    current_line = []
    current_width = 0

    for char in text:
        char_width = get_char_display_width(char)
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


def add_square_line_breaks(traditional_text: str, max_chars: int = 13) -> str:
    """一字语言换行"""
    text = traditional_text.replace("\n", "")
    return "\n".join([text[i : i + max_chars] for i in range(0, len(text), max_chars)])


def add_none_square_line_breaks(traditional_text: str, max_chars: int = 24) -> str:
    """一词多符语言换行"""
    words = traditional_text.split(" ")
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
    text = "\n".join(lines)

    return text


def process_srt_break(subs: pysrt.SubRipFile, square: bool = True, is_horizontal: bool = True) -> pysrt.SubRipFile:
    """处理字幕，根据语言类型和方向进行换行"""
    new_subs = pysrt.SubRipFile()
    index = 0
    for sub in subs:

        # 方块字 如 中文 日语 韩文
        if square:
            max_chars = 13
            if not is_horizontal:
                max_chars = 8
            if len(sub.text) > max_chars * 2:
                # 将字幕按照字数分成2份，时间按照字数平均分配
                text = sub.text.replace("\n", "")
                text1 = text[: int(max_chars * 1.6)]
                text2 = text[int(max_chars * 1.6) :]
                text1 = add_square_line_breaks(text1, max_chars)
                text2 = add_square_line_breaks(text2, max_chars)
                # print(sub.start)
                if text1.strip():
                    sub1 = pysrt.SubRipItem(
                        index=index,
                        start=sub.start,
                        end=sub.start
                        + int((len(text1) / len(text)) * sub.duration.ordinal),
                        text=text1,
                    )
                    new_subs.append(sub1)
                    index += 1
                if text2.strip():
                    sub2 = pysrt.SubRipItem(
                        index=index,
                        start=(
                            sub.start
                            + int((len(text1) / len(text)) * sub.duration.ordinal)
                        ),
                        end=sub.end,
                        text=text2,
                    )
                    new_subs.append(sub2)
                    index += 1
            else:
                sub.text = add_square_line_breaks(sub.text, max_chars)
                sub.index = index
                new_subs.append(sub)
                index += 1
        else:
            max_chars = 24
            if not is_horizontal:
                max_chars = 16
            words = sub.text.split(" ")
            # 按照完整词和词字符长度来分 不把词拆开，长度有不能超
            if len(sub.text) > max_chars:
                text = sub.text.replace("\n", " ")
                logger.debug(f"Processing long subtitle text: {text[:50]}...")
                text1 = ""
                text2 = ""
                for word in words:
                    if len(text1) + len(word) < int(max_chars * 1.6):
                        text1 += word + " "
                    else:
                        text2 += word + " "

                text1 = add_none_square_line_breaks(text1, max_chars)
                text2 = add_none_square_line_breaks(text2, max_chars)

                if text1.strip():
                    sub1 = pysrt.SubRipItem(
                        index=index,
                        start=sub.start,
                        end=sub.start
                        + int((len(text1) / len(text)) * sub.duration.ordinal),
                        text=text1,
                    )
                    new_subs.append(sub1)
                    index += 1
                if text2.strip():
                    sub2 = pysrt.SubRipItem(
                        index=index,
                        start=(
                            sub.start
                            + int((len(text1) / len(text)) * sub.duration.ordinal)
                        ),
                        end=sub.end,
                        text=text2,
                    )
                    new_subs.append(sub2)
                    index += 1
            else:
                sub.text = add_none_square_line_breaks(sub.text, max_chars)
                sub.index = index
                new_subs.append(sub)
                index += 1
    return new_subs


def process_srt_file(srt_file_path: str, square: bool, is_horizontal: bool) -> str:
    """处理字幕文件，应用换行规则"""
    subs = pysrt.open(srt_file_path)
    subs = process_srt_break(subs, square, is_horizontal)
    subs.save(srt_file_path, encoding="utf-8")
    return srt_file_path

