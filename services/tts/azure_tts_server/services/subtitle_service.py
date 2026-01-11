"""字幕处理服务."""

import re
import unicodedata
from datetime import timedelta
from pathlib import Path
from typing import Optional

import pysrt
from models import SentenceInfo
from opencc import OpenCC
from rapidfuzz import fuzz

from config import get_azure_tts_config
from core.exceptions import FileException, ServiceException
from core.logging_config import setup_logging

logger = setup_logging("subtitle_service", log_to_file=True)


class SubtitleService:
    """字幕处理服务."""

    def __init__(self):
        """初始化字幕处理服务."""
        config = get_azure_tts_config()
        self.max_chars_square = config.SUBTITLE_MAX_CHARS_SQUARE
        self.max_chars_non_square = config.SUBTITLE_MAX_CHARS_NON_SQUARE
        self.gap_seconds = config.SUBTITLE_GAP_SECONDS

        self._opencc_s2tw = OpenCC("s2tw")

        logger.info("字幕处理服务初始化完成")

    def save_srt(
        self,
        sentences: list[SentenceInfo],
        srt_file_path: str,
        original_text: str,
    ) -> str:
        """
        将句子信息保存为 SRT 字幕文件.

        Args:
            sentences: 句子信息列表
            srt_file_path: SRT 文件保存路径
            original_text: 原始文本 (用于匹配)

        Returns:
            保存的 SRT 文件路径
        """
        try:
            subs = pysrt.SubRipFile()

            # 判断是否为方块字
            is_square = self._is_square_text(original_text)

            for index, item in enumerate(sentences, start=1):
                start_time = pysrt.SubRipTime(milliseconds=item.start)
                end_time = pysrt.SubRipTime(milliseconds=item.end)
                text = item.raw_text

                # 转换为繁体
                traditional_text = self._opencc_s2tw.convert(text)

                # 从原始文本中匹配最佳文本
                matched_text = self._match_text_from_original(
                    original_text, text, traditional_text, is_square
                )

                if matched_text:
                    traditional_text = matched_text

                sub = pysrt.SubRipItem(
                    index=index,
                    start=start_time,
                    end=end_time,
                    text=traditional_text,
                )
                subs.append(sub)

            # 处理换行
            subs = self._process_line_breaks(subs, is_square)

            # 修复重叠时间
            subs = self._fix_overlapping_subs(subs)

            # 保存文件
            output_path = Path(srt_file_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            subs.save(str(output_path), encoding="utf-8")

            logger.info(f"字幕文件保存成功: {srt_file_path}")
            return srt_file_path

        except (SystemExit, KeyboardInterrupt):
            # 系统退出异常，不捕获，直接抛出
            raise
        except (OSError, PermissionError, FileNotFoundError) as e:
            # 文件系统错误
            logger.error(f"[save_srt] 文件系统错误: {e}", exc_info=True)
            raise FileException(
                f"保存字幕文件失败: {str(e)}",
                file_path=srt_file_path
            ) from e
        except (ValueError, AttributeError) as e:
            # 数据格式错误
            logger.error(f"[save_srt] 数据格式错误: {e}", exc_info=True)
            raise ServiceException(
                f"保存字幕文件失败: {str(e)}",
                service_name="subtitle_service"
            ) from e
        except Exception as e:
            # 其他未预期的异常
            logger.exception(f"[save_srt] 保存字幕文件时发生错误: {e}")
            raise ServiceException(
                f"保存字幕文件失败: {str(e)}",
                service_name="subtitle_service"
            ) from e

    def _is_square_text(self, text: str) -> bool:
        """
        判断文本是否为方块字 (中文、日文、韩文等).

        Args:
            text: 文本内容

        Returns:
            如果是方块字返回 True
        """
        all_char_width = sum(
            self._get_char_display_width(char) for char in text
        )
        return all_char_width > len(text) * 1.5

    def _get_char_display_width(self, char: str) -> int:
        """
        获取字符显示宽度.

        Args:
            char: 字符

        Returns:
            显示宽度 (1 或 2)
        """
        east_asian_width = unicodedata.east_asian_width(char)
        if east_asian_width in ("F", "W", "A"):  # Fullwidth, Wide, Ambiguous
            return 2
        return 1  # Narrow, Halfwidth, Neutral

    def _match_text_from_original(
        self,
        original_text: str,
        simple_text: str,
        traditional_text: str,
        is_square: bool,
    ) -> Optional[str]:
        """
        从原始文本中匹配最佳文本.

        Args:
            original_text: 原始文本
            simple_text: 简体文本
            traditional_text: 繁体文本
            is_square: 是否为方块字

        Returns:
            匹配的文本, 如果未匹配则返回 None
        """
        # 将数字转换为中文
        no_num_text = self._convert_numbers_to_chinese(original_text)

        # 匹配简体
        simple_result = self._find_similar_sentence(
            no_num_text, simple_text, is_square=is_square, threshold=60
        )

        # 匹配繁体
        traditional_result = self._find_similar_sentence(
            no_num_text, traditional_text, is_square=is_square, threshold=60
        )

        # 选择最佳匹配
        if not traditional_result:
            traditional_result = traditional_text
        if not simple_result:
            simple_result = simple_text

        len_simple = len(simple_result) if simple_result else 0
        len_traditional = len(traditional_result) if traditional_result else 0

        if len_simple > len_traditional:
            return simple_result
        elif len_traditional > len_simple:
            return traditional_result
        else:
            return simple_result

    def _find_similar_sentence(
        self,
        long_text: str,
        short_text: str,
        threshold: int = 60,
        tolerance: int = 5,
        is_square: bool = False,
    ) -> Optional[str]:
        """
        从长文本中找到匹配的句子.

        Args:
            long_text: 长文本
            short_text: 短文本
            threshold: 相似度阈值
            tolerance: 长度容差
            is_square: 是否为方块字

        Returns:
            匹配的文本, 如果未匹配则返回 None
        """
        target_len = len(short_text)
        if not is_square:
            long_text = long_text.lower()

        clean_text, index_map = self._clean_and_map(long_text)
        best_score = 0
        best_start = 0
        best_end = 0

        # 滑动窗口搜索
        for i in range(0, len(clean_text) - target_len + 1):
            for delta in range(-tolerance, tolerance + 1):
                end = i + target_len + delta
                if end > len(clean_text) or end <= i:
                    continue
                window = clean_text[i:end]
                score = fuzz.ratio(window, short_text)
                if score > best_score:
                    best_score = score
                    best_start = i
                    best_end = end

        if best_score >= threshold:
            orig_start = index_map[best_start]
            orig_end = index_map[best_end - 1] + 1

            # 检查首尾是否有错别字
            start_score = fuzz.ratio(
                long_text[orig_start:orig_end], short_text[1:]
            )
            end_score = fuzz.ratio(
                long_text[orig_start:orig_end], short_text[:-1]
            )

            if end_score > start_score and end_score > best_score:
                return long_text[orig_start : orig_end + 1].strip()
            elif start_score > end_score and start_score > best_score:
                return long_text[orig_start - 1 : orig_end + 1].strip()

            return long_text[orig_start:orig_end].strip()
        else:
            return None

    def _clean_and_map(self, text: str) -> tuple[str, list[int]]:
        """
        清理文本并建立映射.

        Args:
            text: 原始文本

        Returns:
            (清理后的文本, 索引映射)
        """
        clean = []
        mapping = []
        for i, ch in enumerate(text):
            if re.match(r"\w", ch) or "\u4e00" <= ch <= "\u9fff":
                clean.append(ch)
                mapping.append(i)
        return "".join(clean), mapping

    def _convert_numbers_to_chinese(self, text: str) -> str:
        """
        将数字转换为中文.

        Args:
            text: 原始文本

        Returns:
            转换后的文本
        """
        numbers = re.findall(r"\d+", text)

        num_to_chinese = {
            "0": "零",
            "1": "一",
            "2": "二",
            "3": "三",
            "4": "四",
            "5": "五",
            "6": "六",
            "7": "七",
            "8": "八",
            "9": "九",
        }

        for num in numbers:
            chinese_num = ""
            if len(num) == 1:
                chinese_num = num_to_chinese[num]
            elif len(num) == 2:
                if num[0] == "1":
                    chinese_num = "十" + num_to_chinese[num[1]]
                else:
                    chinese_num = (
                        num_to_chinese[num[0]]
                        + "十"
                        + num_to_chinese[num[1]]
                    )
            elif len(num) == 3:
                chinese_num = (
                    num_to_chinese[num[0]]
                    + "百"
                    + num_to_chinese[num[1]]
                    + "十"
                    + num_to_chinese[num[2]]
                )

            text = text.replace(num, chinese_num)

        return text

    def _process_line_breaks(
        self, subs: pysrt.SubRipFile, is_square: bool
    ) -> pysrt.SubRipFile:
        """
        处理字幕换行.

        Args:
            subs: 字幕文件
            is_square: 是否为方块字

        Returns:
            处理后的字幕文件
        """
        new_subs = pysrt.SubRipFile()
        index = 0

        max_chars = (
            self.max_chars_square if is_square else self.max_chars_non_square
        )

        for sub in subs:
            if is_square:
                processed = self._process_square_subtitle(sub, max_chars)
            else:
                processed = self._process_non_square_subtitle(sub, max_chars)

            for p in processed:
                p.index = index
                new_subs.append(p)
                index += 1

        return new_subs

    def _process_square_subtitle(
        self, sub: pysrt.SubRipItem, max_chars: int
    ) -> list[pysrt.SubRipItem]:
        """处理方块字字幕."""
        text = sub.text.replace("\n", "")
        if len(text) > max_chars * 2:
            # 分成两行
            split_point = int(max_chars * 1.6)
            text1 = text[:split_point]
            text2 = text[split_point:]

            text1 = self._add_square_line_breaks(text1, max_chars)
            text2 = self._add_square_line_breaks(text2, max_chars)

            duration = sub.duration.ordinal
            ratio1 = len(text1) / len(text)

            sub1 = pysrt.SubRipItem(
                index=0,
                start=sub.start,
                end=sub.start + int(duration * ratio1),
                text=text1,
            )
            sub2 = pysrt.SubRipItem(
                index=0,
                start=sub.start + int(duration * ratio1),
                end=sub.end,
                text=text2,
            )

            result = []
            if text1.strip():
                result.append(sub1)
            if text2.strip():
                result.append(sub2)
            return result
        else:
            sub.text = self._add_square_line_breaks(sub.text, max_chars)
            return [sub]

    def _process_non_square_subtitle(
        self, sub: pysrt.SubRipItem, max_chars: int
    ) -> list[pysrt.SubRipItem]:
        """处理非方块字字幕."""
        text = sub.text.replace("\n", " ")
        words = text.split(" ")

        if len(text) > max_chars:
            # 分成两行
            text1 = ""
            text2 = ""
            for word in words:
                if len(text1) + len(word) < int(max_chars * 1.6):
                    text1 += word + " "
                else:
                    text2 += word + " "

            text1 = self._add_non_square_line_breaks(text1, max_chars)
            text2 = self._add_non_square_line_breaks(text2, max_chars)

            duration = sub.duration.ordinal
            ratio1 = len(text1) / len(text)

            sub1 = pysrt.SubRipItem(
                index=0,
                start=sub.start,
                end=sub.start + int(duration * ratio1),
                text=text1,
            )
            sub2 = pysrt.SubRipItem(
                index=0,
                start=sub.start + int(duration * ratio1),
                end=sub.end,
                text=text2,
            )

            result = []
            if text1.strip():
                result.append(sub1)
            if text2.strip():
                result.append(sub2)
            return result
        else:
            sub.text = self._add_non_square_line_breaks(sub.text, max_chars)
            return [sub]

    def _add_square_line_breaks(self, text: str, max_chars: int) -> str:
        """添加方块字换行."""
        text = text.replace("\n", "")
        lines = [
            text[i : i + max_chars]
            for i in range(0, len(text), max_chars)
        ]
        return "\n".join(lines)

    def _add_non_square_line_breaks(self, text: str, max_chars: int) -> str:
        """添加非方块字换行."""
        words = text.split(" ")
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) < max_chars:
                current_line += word + " "
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        return "\n".join(lines)

    def _fix_overlapping_subs(
        self, subs: pysrt.SubRipFile
    ) -> pysrt.SubRipFile:
        """
        修复重叠的字幕时间.

        Args:
            subs: 字幕文件

        Returns:
            修复后的字幕文件
        """
        for i in range(1, len(subs)):
            prev = subs[i - 1]
            curr = subs[i]
            if curr.start < prev.end:
                new_start = self._add_time(
                    prev.end, timedelta(seconds=self.gap_seconds)
                )
                if new_start < curr.end:
                    curr.start = new_start
                else:
                    # 防止时间倒流，设置最小间隔
                    curr.start = self._add_time(
                        prev.end, timedelta(milliseconds=100)
                    )
                    # 确保结束时间大于开始时间
                    if curr.end <= curr.start:
                        curr.end = self._add_time(
                            curr.start, timedelta(seconds=1)
                        )
        return subs

    def _add_time(
        self, srt_time: pysrt.SubRipTime, delta: timedelta
    ) -> pysrt.SubRipTime:
        """
        给 SRT 时间添加时间差.

        Args:
            srt_time: SRT 时间对象
            delta: 时间差

        Returns:
            新的 SRT 时间对象
        """
        total_ms = (
            srt_time.hours * 3600000
            + srt_time.minutes * 60000
            + srt_time.seconds * 1000
            + srt_time.milliseconds
        ) + int(delta.total_seconds() * 1000)

        hours = total_ms // 3600000
        minutes = (total_ms % 3600000) // 60000
        seconds = (total_ms % 60000) // 1000
        milliseconds = total_ms % 1000

        return pysrt.SubRipTime(
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            milliseconds=milliseconds,
        )

