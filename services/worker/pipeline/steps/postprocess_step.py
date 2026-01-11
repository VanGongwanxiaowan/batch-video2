"""后期处理步骤

添加字幕、Logo、水印等后期处理。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 PostProcessResult
"""
import os
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

from core.config.api import SubtitleStyleConfig
from core.logging_config import setup_logging
from core.utils.ffmpeg import run_ffmpeg
from core.utils.ffmpeg.builder import FFmpegCommandBuilder

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import PostProcessResult

logger = setup_logging("worker.pipeline.steps.postprocess")


class PostProcessingStep(BaseStep):
    """后期处理步骤

    功能:
    1. 添加字幕到视频
    2. 添加 Logo 水印
    3. 合成音频到视频
    4. 视频格式转换

    输入 (context/kwargs):
    - combined_video: 合成的视频
    - audio_path: 音频文件
    - srt_path: 字幕文件
    - logopath: Logo 文件路径
    - workspace_dir: 工作目录

    输出 (PostProcessResult):
    - final_video_path: 最终视频路径
    - processing_steps: 应用的处理步骤列表
    """

    name = "PostProcessing"
    description = "后期处理和合成"

    # 启用函数式模式
    _functional_mode = True

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        combined_video = getattr(context, 'combined_video', None)
        if not combined_video:
            raise ValueError("没有可用的视频文件")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行后期处理（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.final_video_path = result.data.get("final_video_path")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "PostProcessResult":
        """执行后期处理（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数

        Returns:
            PostProcessResult: 包含 final_video_path, processing_steps 的结果
        """
        from ..results import PostProcessResult

        logger.info(
            f"[{self.name}] 开始后期处理 "
            f"(job_id={context.job_id})"
        )

        # 准备输出路径
        workspace = Path(context.workspace_dir)
        output_dir = workspace / "final"
        output_dir.mkdir(parents=True, exist_ok=True)

        final_video_path = str(output_dir / "final.mp4")

        # 记录处理步骤
        processing_steps = []

        # 合成音频
        video_with_audio = self._add_audio_to_video(
            context,
            output_dir / "with_audio.mp4",
        )
        processing_steps.append("add_audio")

        # 添加字幕
        srt_path = getattr(context, 'srt_path', None)
        if srt_path and os.path.exists(srt_path):
            video_with_subtitle = self._add_subtitle_to_video(
                context,
                video_with_audio,
                output_dir / "with_subtitle.mp4",
            )
            processing_steps.append("add_subtitle")
        else:
            video_with_subtitle = video_with_audio

        # 添加 Logo
        logopath = getattr(context, 'logopath', None)
        if logopath and os.path.exists(logopath):
            final_video = self._add_logo_to_video(
                context,
                video_with_subtitle,
                final_video_path,
            )
            processing_steps.append("add_logo")
        else:
            import shutil
            shutil.copy(video_with_subtitle, final_video_path)
            final_video = final_video_path

        logger.info(
            f"[{self.name}] 后期处理完成 "
            f"(job_id={context.job_id}, output={final_video_path})"
        )

        # 返回函数式结果
        return PostProcessResult(
            step_name=self.name,
            final_video_path=final_video_path,
            processing_steps=processing_steps
        )

    def _add_audio_to_video(
        self,
        context: PipelineContext,
        output_path: Path,
    ) -> str:
        """添加音频到视频

        Args:
            context: Pipeline 上下文
            output_path: 输出路径

        Returns:
            str: 处理后的视频路径
        """
        from core.utils.ffmpeg import FFmpegError

        # 使用 FFmpegCommandBuilder 构建命令
        command = (FFmpegCommandBuilder()
                   .add_input(context.combined_video, index=0)
                   .add_input(context.audio_path, index=1)
                   .set_video_codec("copy")
                   .set_audio_codec("aac")
                   .add_option("shortest", "")
                   .set_output(str(output_path))
                   .build())

        try:
            run_ffmpeg(command, timeout=300)
        except FFmpegError as exc:
            logger.error(f"[{self.name}] 添加音频失败: {exc}")
            raise

        return str(output_path)

    def _add_subtitle_to_video(
        self,
        context: PipelineContext,
        input_video: str,
        output_path: Path,
    ) -> str:
        """添加字幕到视频

        Args:
            context: Pipeline 上下文
            input_video: 输入视频路径
            output_path: 输出路径

        Returns:
            str: 处理后的视频路径
        """
        from core.utils.ffmpeg import FFmpegError

        # 使用 SubtitleStyleConfig 获取字幕样式
        font = SubtitleStyleConfig.DEFAULT_FONT
        font_size = SubtitleStyleConfig.DEFAULT_FONT_SIZE
        primary_color = SubtitleStyleConfig.color_to_hex(SubtitleStyleConfig.DEFAULT_FONT_COLOR)
        outline_color = SubtitleStyleConfig.color_to_hex(SubtitleStyleConfig.DEFAULT_OUTLINE_COLOR)

        # 使用 subtitles 滤镜添加字幕
        vf_filter = (f"subtitles='{context.srt_path}':force_style="
                     f"FontName={font},FontSize={font_size},"
                     f"PrimaryColour=&H{primary_color},"
                     f"OutlineColour=&H{outline_color}'")

        # 使用 FFmpegCommandBuilder 构建命令
        command = (FFmpegCommandBuilder()
                   .add_input(input_video)
                   .add_option("vf", vf_filter)
                   .set_audio_codec("copy")
                   .set_output(str(output_path))
                   .build())

        try:
            run_ffmpeg(command, timeout=300)
        except FFmpegError as exc:
            logger.error(f"[{self.name}] 添加字幕失败: {exc}")
            raise

        return str(output_path)

    def _add_logo_to_video(
        self,
        context: PipelineContext,
        input_video: str,
        output_path: str,
    ) -> str:
        """添加 Logo 到视频

        Args:
            context: Pipeline 上下文
            input_video: 输入视频路径
            output_path: 输出路径

        Returns:
            str: 处理后的视频路径
        """
        from core.utils.ffmpeg import FFmpegError

        # 使用配置常量
        logo_scale_width = SubtitleStyleConfig.LOGO_SCALE_WIDTH
        output_label = SubtitleStyleConfig.FFMPEG_OUTPUT_LABEL

        # 使用 overlay 滤镜添加 Logo（右上角）
        # Logo 在右上角: W-w-10:10
        command = (FFmpegCommandBuilder()
                   .add_input(input_video, index=0)
                   .add_input(context.logopath, index=1)
                   .add_option("filter_complex",
                               f"[1:v]scale={logo_scale_width}:-1[logo];[0:v][logo]=W-w-10:10{output_label}")
                   .map_stream(output_label)
                   .set_audio_codec("copy")
                   .set_output(output_path)
                   .build())

        try:
            run_ffmpeg(command, timeout=300)
        except FFmpegError as exc:
            logger.error(f"[{self.name}] 添加 Logo 失败: {exc}")
            raise

        return output_path

    def _context_to_result(self, context: PipelineContext) -> "PostProcessResult":
        """将 PipelineContext 转换为 PostProcessResult

        Args:
            context: Pipeline 上下文

        Returns:
            PostProcessResult
        """
        from ..results import PostProcessResult

        final_video_path = getattr(context, 'final_video_path', None)

        return PostProcessResult(
            step_name=self.name,
            final_video_path=final_video_path,
            processing_steps=[]
        )


__all__ = [
    "PostProcessingStep",
]
