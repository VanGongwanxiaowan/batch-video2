"""视频合成步骤

将生成的图片合成为视频，添加转场效果。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 VideoResult

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution
- 使用 VideoProcessingConfig 获取视频处理参数
- 使用 FFmpegCommandBuilder 构建命令
- 替换硬编码的 1360:768 分辨率
- 支持并行 FFmpeg 执行（性能优化）
"""
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from concurrent.futures.process import _threads_wakeups
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING, Tuple

from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import (
    VideoResolution,
    VideoProcessingConfig,
    get_video_config,
    DEFAULT_LANDSCAPE_CONFIG,
)
# 使用 FFmpeg 命令构建器和执行器
from core.utils.ffmpeg import FFmpegError, run_ffmpeg
from core.utils.ffmpeg.builder import FFmpegCommandBuilder, build_concat_command

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import VideoResult

logger = setup_logging("worker.pipeline.steps.video")


class VideoCompositionStep(BaseStep):
    """视频合成步骤

    功能:
    1. 将静态图片转换为视频
    2. 添加转场效果
    3. 合并所有视频片段
    4. 添加背景音乐

    输入 (context/kwargs):
    - image_paths: 图像路径列表
    - audio_path: 音频文件路径
    - workspace_dir: 工作目录
    - is_horizontal: 横竖屏标志

    输出 (VideoResult):
    - video_path: 合成后的视频路径
    - duration: 视频时长
    - segment_count: 视频片段数

    代码重构说明:
    - 使用统一的 VideoProcessingConfig 获取视频参数
    - 不再硬编码 FPS 和持续时间等魔法数字
    - 支持并行 FFmpeg 执行（可通过 enable_parallel 和 max_workers 控制）
    """

    name = "VideoComposition"
    description = "视频合成和转场效果"

    # 使用统一配置（默认横屏）
    _config: VideoProcessingConfig = DEFAULT_LANDSCAPE_CONFIG

    # 并行处理配置
    # 设置为 True 启用并行 FFmpeg 执行（性能优化）
    # 注意：需要根据 CPU 核心数调整 max_workers
    enable_parallel = True  # 默认启用并行处理
    max_workers = 4  # 最大并行进程数（建议设置为 CPU 核心数）

    # 转场类型（从配置获取）
    @property
    def TRANSITION_TYPES(self) -> tuple:
        return self._config.transition_types

    # 启用函数式模式
    _functional_mode = True

    # ========================================================================
    # 静态方法（用于并行处理，可被 pickle 序列化）
    # ========================================================================

    @staticmethod
    def _image_to_video_static(
        image_path: str,
        output_path: str,
        duration: float,
        width: int,
        height: int,
        video_codec: str,
        crf: int,
        preset: str,
        pix_fmt: str,
        fps: int,
        ffmpeg_timeout: int,
        transition: str = "fade",
    ) -> None:
        """静态方法：将图片转换为视频（可被序列化到子进程）

        此方法必须是静态的且只接受简单参数，以便能够被
        ProcessPoolExecutor 正确序列化到子进程中执行。

        Args:
            image_path: 图片路径
            output_path: 输出视频路径
            duration: 持续时间（秒）
            width: 视频宽度
            height: 视频高度
            video_codec: 视频编解码器
            crf: CRF 质量值
            preset: 编码速度预设
            pix_fmt: 像素格式
            fps: 帧率
            ffmpeg_timeout: FFmpeg 超时时间（秒）
            transition: 转场类型
        """
        # 使用 FFmpegCommandBuilder 构建命令
        command = (FFmpegCommandBuilder()
                   .add_input(image_path, options={"loop": "1", "t": str(duration)})
                   .add_scale_filter(width, height, force_original=True)
                   .map_stream("[scaled]")
                   .set_video_codec(video_codec)
                   .set_quality(crf=crf, preset=preset)
                   .set_pixel_format(pix_fmt)
                   .set_fps(fps)
                   .add_option("tune", "stillimage")
                   .set_output(output_path)
                   .build())

        try:
            run_ffmpeg(command, timeout=ffmpeg_timeout)
        except FFmpegError as exc:
            # 在子进程中记录错误
            import logging
            logging.error(f"[_image_to_video_static] FFmpeg 失败: {exc}")
            raise

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        image_paths = getattr(context, 'image_paths', None)
        if not image_paths:
            raise ValueError("没有图像文件")

        audio_path = getattr(context, 'audio_path', None)
        if not audio_path or not os.path.exists(audio_path):
            raise ValueError("音频文件不存在")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行视频合成（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.combined_video = result.data.get("video_path")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "VideoResult":
        """执行视频合成（函数式模式）

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数，可以包含 image_paths, audio_path

        Returns:
            VideoResult: 包含 video_path, duration, segment_count 的结果
        """
        from ..results import VideoResult

        # 从 kwargs 或 context 获取参数
        image_paths = kwargs.get("image_paths")
        if not image_paths:
            image_paths = getattr(context, 'image_paths', None)

        if not image_paths:
            raise ValueError("需要 image_paths 参数")

        logger.info(
            f"[{self.name}] 开始视频合成 "
            f"(job_id={context.job_id}, 图像数={len(image_paths)})"
        )

        # 准备输出路径
        workspace = Path(context.workspace_dir)
        output_dir = workspace / "videos"
        output_dir.mkdir(parents=True, exist_ok=True)

        combined_video_path = str(output_dir / "combined.mp4")

        # 为每张图片生成视频片段
        video_segments = self._create_video_segments(
            context,
            image_paths,
            output_dir,
        )

        # 合并视频片段
        self._merge_video_segments(
            context,
            video_segments,
            combined_video_path,
        )

        # 计算时长（使用配置中的持续时间）
        duration = len(video_segments) * self._config.duration_per_image

        logger.info(
            f"[{self.name}] 视频合成完成 "
            f"(job_id={context.job_id}, output={combined_video_path})"
        )

        # 返回函数式结果
        return VideoResult(
            step_name=self.name,
            video_path=combined_video_path,
            duration=duration,
            segment_count=len(video_segments)
        )

    def _create_video_segments(
        self,
        context: PipelineContext,
        image_paths: List[str],
        output_dir: Path,
    ) -> List[str]:
        """创建视频片段

        根据配置自动选择串行或并行执行：
        - 如果 image_paths 数量 >= 3 且 enable_parallel=True，则使用并行处理
        - 否则使用串行处理（避免小批量任务的进程创建开销）

        Args:
            context: Pipeline 上下文
            image_paths: 图像路径列表
            output_dir: 输出目录

        Returns:
            List[str]: 视频片段路径列表
        """
        # 根据横竖屏获取配置
        config = get_video_config(context.is_horizontal)

        # 准备输出路径列表
        segment_paths = [
            str(output_dir / f"segment_{i:03d}.mp4")
            for i in range(len(image_paths))
        ]

        # 决定使用并行还是串行处理
        # 至少3张图片才启用并行，避免小批量的进程创建开销
        use_parallel = (
            self.enable_parallel and
            len(image_paths) >= 3 and
            self.max_workers > 1
        )

        if use_parallel:
            logger.info(
                f"[{self.name}] 使用并行模式创建视频段 "
                f"(image_count={len(image_paths)}, max_workers={self.max_workers})"
            )
            return self._create_segments_parallel(
                image_paths, segment_paths, config
            )
        else:
            logger.info(
                f"[{self.name}] 使用串行模式创建视频段 "
                f"(image_count={len(image_paths)})"
            )
            return self._create_segments_sequential(
                image_paths, segment_paths, config
            )

    def _create_segments_sequential(
        self,
        image_paths: List[str],
        segment_paths: List[str],
        config: VideoProcessingConfig,
    ) -> List[str]:
        """串行创建视频片段（原有逻辑，保持不变）

        Args:
            image_paths: 图像路径列表
            segment_paths: 输出视频路径列表
            config: 视频处理配置

        Returns:
            List[str]: 视频片段路径列表
        """
        segments = []
        transition_types = config.transition_types

        for i, image_path in enumerate(image_paths):
            segment_path = segment_paths[i]

            # 为图片添加动效并转换为视频
            self._image_to_video(
                image_path=image_path,
                output_path=segment_path,
                duration=config.duration_per_image,
                transition=transition_types[i % len(transition_types)],
                config=config,
            )

            segments.append(segment_path)

        return segments

    def _create_segments_parallel(
        self,
        image_paths: List[str],
        segment_paths: List[str],
        config: VideoProcessingConfig,
    ) -> List[str]:
        """并行创建视频片段（性能优化）

        使用 ProcessPoolExecutor 并行执行 FFmpeg 进程，
        在多核 CPU 上可获得显著的性能提升。

        Args:
            image_paths: 图像路径列表
            segment_paths: 输出视频路径列表
            config: 视频处理配置

        Returns:
            List[str]: 视频片段路径列表

        Raises:
            Exception: 如果任何 FFmpeg 进程失败
        """
        segments = []
        transition_types = config.transition_types

        # 准备任务参数列表
        tasks = [
            (
                image_paths[i],
                segment_paths[i],
                config.duration_per_image,
                config.width,
                config.height,
                config.video_codec,
                config.crf,
                config.preset,
                config.pix_fmt,
                config.fps,
                config.ffmpeg_timeout,
                transition_types[i % len(transition_types)],
            )
            for i in range(len(image_paths))
        ]

        # 使用进程池并行执行
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            futures = {
                executor.submit(self._image_to_video_static, *task): i
                for i, task in enumerate(tasks)
            }

            # 等待所有任务完成
            completed = 0
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    future.result()  # 获取结果或异常
                    completed += 1
                    logger.debug(
                        f"[{_create_segments_parallel.__name__}] "
                        f"片段 {idx+1}/{len(image_paths)} 完成"
                    )
                except Exception as exc:
                    logger.error(
                        f"[{_create_segments_parallel.__name__}] "
                        f"片段 {idx+1} 失败: {exc}"
                    )
                    raise

        logger.info(
            f"[{_create_segments_parallel.__name__}] "
            f"并行创建完成: {completed}/{len(image_paths)} 个片段"
        )

        return segment_paths

    def _image_to_video(
        self,
        image_path: str,
        output_path: str,
        duration: float,
        transition: str,
        config: VideoProcessingConfig,
    ) -> None:
        """将图片转换为视频

        Args:
            image_path: 图片路径
            output_path: 输出视频路径
            duration: 持续时间（秒）
            transition: 转场类型
            config: 视频处理配置（包含分辨率等参数）

        代码重构说明：
            使用 FFmpegCommandBuilder 构建命令
        """
        # 使用 FFmpegCommandBuilder 构建命令
        command = (FFmpegCommandBuilder()
                   .add_input(image_path, options={"loop": "1", "t": str(duration)})
                   .add_scale_filter(config.width, config.height, force_original=True)
                   .map_stream("[scaled]")
                   .set_video_codec(config.video_codec)
                   .set_quality(crf=config.crf, preset=config.preset)
                   .set_pixel_format(config.pix_fmt)
                   .set_fps(config.fps)
                   .add_option("tune", "stillimage")
                   .set_output(output_path)
                   .build())

        try:
            run_ffmpeg(command, timeout=config.ffmpeg_timeout)
        except FFmpegError as exc:
            logger.error(f"ffmpeg 失败: {exc}")
            raise

    def _merge_video_segments(
        self,
        context: PipelineContext,
        segments: List[str],
        output_path: str,
    ) -> None:
        """合并视频片段

        Args:
            context: Pipeline 上下文
            segments: 视频片段路径列表
            output_path: 输出视频路径

        代码重构说明：
            使用 build_concat_command 便捷函数
        """
        # 使用便捷函数构建合并命令
        command = build_concat_command(segments, output_path, method="concat")

        try:
            run_ffmpeg(command, timeout=300)
        except FFmpegError as exc:
            logger.error(f"ffmpeg 合并失败: {exc}")
            raise

    def _context_to_result(self, context: PipelineContext) -> "VideoResult":
        """将 PipelineContext 转换为 VideoResult

        Args:
            context: Pipeline 上下文

        Returns:
            VideoResult
        """
        from ..results import VideoResult

        video_path = getattr(context, 'combined_video', None)

        return VideoResult(
            step_name=self.name,
            video_path=video_path,
            duration=0.0,
            segment_count=0
        )


__all__ = [
    "VideoCompositionStep",
]
