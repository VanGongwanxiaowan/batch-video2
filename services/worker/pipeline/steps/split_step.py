"""文本分镜步骤

将长文本按照时间切分为多个分镜片段。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 SplitResult
"""
import json
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from core.config.api import TextProcessingConfig
from core.logging_config import setup_logging

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import SplitResult

logger = setup_logging("worker.pipeline.steps.split")


class TextSplitStep(BaseStep):
    """文本分镜步骤

    功能:
    1. 解析字幕文件获取时间戳
    2. 按时间切分文本为多个片段
    3. 为每个片段生成图像生成提示词
    4. 生成分镜配置 JSON 文件

    输入 (context/kwargs):
    - content: 原始文本
    - srt_path: 字幕文件路径
    - workspace_dir: 工作目录

    输出 (SplitResult):
    - splits: 分镜数据列表
    """

    name = "TextSplit"
    description = "文本分镜切分"

    # 分镜时长范围（秒）
    MIN_SPLIT_DURATION = 5
    MAX_SPLIT_DURATION = 15

    # 启用函数式模式
    _functional_mode = True

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        if not context.content:
            raise ValueError("文本内容不能为空")

        srt_path = getattr(context, 'srt_path', None)
        if not srt_path or not os.path.exists(srt_path):
            raise ValueError("字幕文件不存在")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行分镜（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.splits = result.data.get("splits")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "SplitResult":
        """执行分镜（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数，可以包含 srt_path

        Returns:
            SplitResult: 包含 splits 的结果
        """
        from ..results import SplitResult

        # 从 kwargs 或 context 获取 srt_path
        srt_path = kwargs.get("srt_path")
        if not srt_path:
            srt_path = getattr(context, 'srt_path', None)

        if not srt_path:
            raise ValueError("需要 srt_path 参数")

        logger.info(
            f"[{self.name}] 开始文本分镜 "
            f"(job_id={context.job_id})"
        )

        # 解析字幕文件
        subtitles = self._parse_srt(srt_path)

        # 生成分镜数据
        splits = self._create_splits(context, subtitles)

        # 保存分镜配置
        self._save_splits_config(context, splits)

        logger.info(
            f"[{self.name}] 分镜完成 "
            f"(job_id={context.job_id}, 分镜数={len(splits)})"
        )

        # 返回函数式结果
        return SplitResult(
            step_name=self.name,
            splits=splits
        )

    def _parse_srt(self, srt_path: str) -> List[dict]:
        """解析 SRT 字幕文件

        Args:
            srt_path: 字幕文件路径

        Returns:
            List[dict]: 字幕列表，每项包含 index, start, end, text
        """
        subtitles = []

        with open(srt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行
            if not line:
                i += 1
                continue

            # 解析序号
            try:
                index = int(line)
            except ValueError:
                i += 1
                continue

            # 解析时间戳
            if i + 1 >= len(lines):
                break
            time_line = lines[i + 1].strip()
            start_ms, end_ms = self._parse_time_line(time_line)

            # 解析文本
            text_lines = []
            i += 2
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1

            subtitles.append({
                "index": index,
                "start": start_ms,
                "end": end_ms,
                "text": "".join(text_lines),
            })

            i += 1

        return subtitles

    def _parse_time_line(self, time_line: str) -> tuple:
        """解析 SRT 时间戳行

        Args:
            time_line: 时间戳行，格式 "00:00:00,000 --> 00:00:05,000"

        Returns:
            tuple: (start_ms, end_ms) 毫秒
        """
        parts = time_line.split("-->")
        start_str = parts[0].strip()
        end_str = parts[1].strip()

        def time_to_ms(time_str: str) -> int:
            """将 SRT 时间转换为毫秒"""
            time_str, ms_str = time_str.split(",")
            h, m, s = time_str.split(":")
            return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms_str)

        return time_to_ms(start_str), time_to_ms(end_str)

    def _create_splits(self, context: PipelineContext, subtitles: List[dict]) -> List[dict]:
        """创建分镜数据

        Args:
            context: Pipeline 上下文
            subtitles: 字幕列表

        Returns:
            List[dict]: 分镜列表
        """
        splits = []
        current_split = []
        split_start_ms = None

        for subtitle in subtitles:
            if split_start_ms is None:
                split_start_ms = subtitle["start"]

            current_split.append(subtitle["text"])

            # 计算当前分镜时长
            duration_ms = subtitle["end"] - split_start_ms
            duration_sec = duration_ms / 1000

            # 如果超过最大时长或文本过长，创建新分镜
            if duration_sec >= self.MAX_SPLIT_DURATION or len("".join(current_split)) > TextProcessingConfig.MAX_SPLIT_TEXT_LENGTH:
                splits.append({
                    "index": len(splits),
                    "start": split_start_ms,
                    "end": subtitle["end"],
                    "text": "".join(current_split),
                    "prompt": self._generate_prompt(context, "".join(current_split)),
                })
                current_split = []
                split_start_ms = subtitle["end"]

        # 处理最后一个分镜
        if current_split:
            splits.append({
                "index": len(splits),
                "start": split_start_ms,
                "end": subtitles[-1]["end"],
                "text": "".join(current_split),
                "prompt": self._generate_prompt(context, "".join(current_split)),
            })

        return splits

    def _generate_prompt(self, context: PipelineContext, text: str) -> str:
        """生成图像提示词

        Args:
            context: Pipeline 上下文
            text: 文本内容

        Returns:
            str: 提示词
        """
        # 获取话题提示词前缀
        topic = context.job.topic if context.job else None
        prefix = ""

        if topic and topic.prompt_image_prefix:
            prefix = topic.prompt_image_prefix

        # 组合提示词
        prompt = f"{prefix} {text}".strip()
        return prompt

    def _save_splits_config(self, context: PipelineContext, splits: List[dict]) -> None:
        """保存分镜配置到 JSON 文件

        Args:
            context: Pipeline 上下文
            splits: 分镜数据
        """
        workspace = Path(context.workspace_dir)
        config_path = workspace / "splits.json"

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"splits": splits}, f, ensure_ascii=False, indent=2)

        logger.debug(
            f"[{self.name}] 分镜配置已保存 "
            f"(job_id={context.job_id}, path={config_path})"
        )

    def _context_to_result(self, context: PipelineContext) -> "SplitResult":
        """将 PipelineContext 转换为 SplitResult

        Args:
            context: Pipeline 上下文

        Returns:
            SplitResult
        """
        from ..results import SplitResult

        splits = getattr(context, 'splits', [])

        return SplitResult(
            step_name=self.name,
            splits=splits
        )


__all__ = [
    "TextSplitStep",
]
