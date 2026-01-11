"""
文本处理工具模块
从 pipe_line.py 中提取的文本处理相关函数
"""

import re
import unicodedata
from typing import List


def get_char_display_width(char: str) -> int:
    """
    根据字符的东亚宽度属性确定显示宽度。
    'F' (Fullwidth) 和 'W' (Wide) 字符通常宽度为 2。
    'Na' (Narrow), 'H' (Halfwidth), 'N' (Neutral) 字符通常宽度为 1。
    'A' (Ambiguous) 字符被视为宽度 2，以便更安全的换行。
    """
    east_asian_width = unicodedata.east_asian_width(char)
    if east_asian_width in ("F", "W", "A"):  # Fullwidth, Wide, Ambiguous
        return 2
    return 1  # Narrow, Halfwidth, Neutral


def cjk_aware_len(text: str) -> int:
    """
    计算字符串长度，将CJK字符视为2个单位，其他字符视为1个单位。
    """
    length = 0
    for char in text:
        # 检查字符是否在常见的CJK Unicode范围内
        if (
            "\u4e00" <= char <= "\u9fff"
            or "\u3040" <= char <= "\u30ff"
            or "\uac00" <= char <= "\ud7af"
        ):
            length += 2
        else:
            length += 1
    return length


def split_string_by_punctuation(text: str, min_length: int = 15) -> List[str]:
    """
    按标点符号分割字符串，确保每个部分至少为 min_length
    (其中CJK字符计为2)。如果某个部分太短，尝试与下一个可用部分合并。
    标点符号保留在前面的文本中。
    """
    # 用于分割的标点符号模式，同时保留标点符号本身
    pattern = r"([!·，。！？；,.!?;、\-—–—])"
    parts = re.split(pattern, text)

    # 清理部分：文本、标点符号、文本、标点符号...
    # 过滤掉可能因在开头/结尾分割或双标点符号而产生的空字符串
    cleaned_parts = [
        part.strip() for part in parts if part.strip() or re.match(pattern, part)
    ]

    processed_segments = []
    current_segment = ""

    for i, part in enumerate(cleaned_parts):
        if re.match(pattern, part):  # 它是标点符号
            if current_segment:  # 只有在有段可附加时才添加标点符号
                current_segment += part
            # 如果 current_segment 为空且 'part' 是标点符号，意味着字符串以标点符号开头
            # 或者有双标点符号。我们让它被吸收或忽略（如果没有前面的文本）。
        else:  # 它是文本段
            if current_segment:  # 如果有现有段，这个新文本需要追加
                current_segment += part
            else:  # 否则，这是新段的开始
                current_segment = part

        # 处理部分后，检查 current_segment 是否足够长，或者是否是最后一部分
        # 我们在下一个潜在文本部分开始之前检查长度，以包括附加的标点符号（如果有）
        if i + 1 < len(cleaned_parts) and not re.match(pattern, cleaned_parts[i + 1]):
            # 如果下一部分是文本，意味着 current_segment 已累积其关联的标点符号（如果有）
            # 现在，评估 current_segment 是否应该最终确定。
            if cjk_aware_len(current_segment) >= min_length:
                processed_segments.append(current_segment)
                current_segment = ""
        elif i == len(cleaned_parts) - 1:  # 这是输入文本的最后一个部分
            if processed_segments and cjk_aware_len(current_segment) < min_length:
                processed_segments[-1] += current_segment
            else:
                processed_segments.append(current_segment)

    results = []
    # 最终清理：移除前导/尾随特定标点符号
    for part in processed_segments:
        txt = part.strip().replace("\n", "")
        # 仅在剥离后位于段的非常末尾或开头时移除
        txt = re.sub(
            r"^[，。！？；,.!?;、\-—–—]+", "", txt
        )  # 移除前导标点符号
        txt = re.sub(
            r"[，。！？；,.!?;、\-—–—]+$", "", txt
        )  # 移除尾随标点符号
        txt = txt.strip(
            '"'
        )  # 如果它们在一般标点符号移除后仍然存在，则移除特定引号
        results.append(txt)

    new_results = []
    # 移除开头和结尾的 ， 。 不需要的符号
    for i, part in enumerate(results):
        txt = part.strip(",")
        txt = txt.strip("。")
        txt = txt.strip("，")
        txt = txt.strip("、")
        txt = txt.strip('"')
        txt = txt.strip(":")
        txt = txt.strip(".")
        txt = txt.strip("!")
        txt = txt.strip(".")
        txt = txt.replace("\n", "")
        new_results.append(txt)
    return [s for s in new_results if s]

