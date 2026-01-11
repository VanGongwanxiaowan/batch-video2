"""字幕生成步骤

处理字幕文件，包括格式转换、繁简转换等。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 SubtitleResult
"""
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from core.config.api import ConfigFilePaths, TextProcessingConfig
from core.logging_config import setup_logging

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import SubtitleResult

logger = setup_logging("worker.pipeline.steps.subtitle")


class SubtitleGenerationStep(BaseStep):
    """字幕生成处理步骤

    功能:
    1. 验证字幕文件格式
    2. 可选：转换为繁体字幕
    3. 可选：调整字幕样式

    输入 (context/kwargs):
    - srt_path: 原始字幕文件路径
    - extra.language_config: 语言配置

    输出 (SubtitleResult):
    - srt_path: 处理后的字幕文件路径
    - subtitle_count: 字幕条数
    """

    name = "SubtitleGeneration"
    description = "字幕文件处理和格式化"

    # 启用函数式模式
    _functional_mode = True

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        srt_path = getattr(context, 'srt_path', None)
        if not srt_path:
            raise ValueError("字幕文件路径未设置")

        if not os.path.exists(srt_path):
            raise FileNotFoundError(f"字幕文件不存在: {srt_path}")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行字幕处理（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # SubtitleResult 不需要更新 context（srt_path 已存在）
        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "SubtitleResult":
        """执行字幕处理（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数，可以包含 srt_path

        Returns:
            SubtitleResult: 包含 srt_path, subtitle_count 的结果
        """
        from ..results import SubtitleResult

        # 从 kwargs 或 context 获取 srt_path
        srt_path = kwargs.get("srt_path")
        if not srt_path:
            srt_path = getattr(context, 'srt_path', None)

        if not srt_path:
            raise ValueError("需要 srt_path 参数")

        logger.info(
            f"[{self.name}] 开始处理字幕 "
            f"(job_id={context.job_id}, srt={srt_path})"
        )

        # 检查是否需要转换为繁体
        if self._should_convert_to_traditional(context):
            self._convert_to_traditional_chinese(srt_path)
            logger.info(f"[{self.name}] 字幕已转换为繁体 (job_id={context.job_id})")

        # 验证字幕格式并获取条数
        subtitle_count = self._validate_srt_format(srt_path)

        logger.info(f"[{self.name}] 字幕处理完成 (job_id={context.job_id})")

        # 返回函数式结果
        return SubtitleResult(
            step_name=self.name,
            srt_path=srt_path,
            subtitle_count=subtitle_count
        )

    def _should_convert_to_traditional(self, context: PipelineContext) -> bool:
        """判断是否需要转换为繁体

        Args:
            context: Pipeline 上下文

        Returns:
            bool: 是否需要转换
        """
        # 检查语言配置或任务配置
        lang_config = context.extra.get("language_config", {})
        return lang_config.get("traditional_chinese", False)

    def _convert_to_traditional_chinese(self, srt_path: str) -> None:
        """转换为繁体中文

        Args:
            srt_path: 字幕文件路径
        """
        try:
            import opencc

            # 读取简体字幕
            with open(srt_path, "r", encoding="utf-8") as f:
                simplified = f.read()

            # 转换为繁体（使用配置常量）
            converter = opencc.OpenCC(ConfigFilePaths.OPENCC_S2T_CONFIG)
            traditional = converter.convert(simplified)

            # 写回文件
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(traditional)

        except ImportError:
            logger.warning("opencc 未安装，跳过繁体转换")
        except Exception as exc:
            logger.error(f"繁体转换失败: {exc}")

    def _validate_srt_format(self, srt_path: str) -> int:
        """验证 SRT 格式

        Args:
            srt_path: 字幕文件路径

        Returns:
            int: 字幕条数
        """
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 简单验证：检查是否包含 SRT 时间格式
            if "-->" not in content:
                raise ValueError("字幕文件格式无效：缺少时间戳")

            # 统计字幕条数（使用配置常量）
            subtitle_count = content.count(TextProcessingConfig.DOUBLE_NEWLINE)
            logger.debug(
                f"[{self.name}] 字幕条数: {subtitle_count}"
            )

            return subtitle_count

        except Exception as exc:
            logger.error(f"SRT 格式验证失败: {exc}")
            raise

    def _context_to_result(self, context: PipelineContext) -> "SubtitleResult":
        """将 PipelineContext 转换为 SubtitleResult

        Args:
            context: Pipeline 上下文

        Returns:
            SubtitleResult
        """
        from ..results import SubtitleResult

        srt_path = getattr(context, 'srt_path', None)
        subtitle_count = 0

        if srt_path and os.path.exists(srt_path):
            subtitle_count = self._validate_srt_format(srt_path)

        return SubtitleResult(
            step_name=self.name,
            srt_path=srt_path,
            subtitle_count=subtitle_count
        )


__all__ = [
    "SubtitleGenerationStep",
]
