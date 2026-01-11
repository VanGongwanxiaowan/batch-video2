"""图像生成步骤

为每个分镜生成对应的配图。

支持两种执行模式：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 ImageResult

依赖倒置原则改进：
- 依赖 IImageGenerationService 抽象接口而非具体实现
- 支持依赖注入，便于测试和替换实现

使用服务层的并行图片生成，大幅提升性能。

代码重构说明：
- 使用 core.config.video_config 中的统一 VideoResolution 枚举
- 移除本地定义的 ImageResolution 枚举，避免重复
- 保持向后兼容，旧代码注释保留
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import time

from config import settings
from core.interfaces.service_interfaces import IImageGenerationService
from core.logging_config import setup_logging
# 使用统一的视频配置
from core.config.video_config import VideoResolution, VideoProcessingConfig

from .base import BaseStep
from ..context import PipelineContext

if TYPE_CHECKING:
    from ..results import ImageResult

logger = setup_logging("worker.pipeline.steps.image")


# ============================================================================
# 常量配置 - 使用统一的 VideoResolution
# ============================================================================

# 旧的 ImageResolution 枚举已移至 core.config.video_config.VideoResolution
# 以下为备份参考（已废弃，请使用 VideoResolution）:
# class ImageResolution(Enum):
#     LANDSCAPE_HD = (1360, 768)
#     PORTRAIT_HD = (768, 1360)
#     ...

# VideoResolution 提供了更多功能:
# - resolution.width / resolution.height: 获取宽高
# - resolution.is_landscape() / resolution.is_portrait(): 判断方向
# - resolution.swap(): 旋转90度
# - VideoResolution.for_orientation(is_horizontal): 根据方向获取


@dataclass
class GenerationConfig:
    """图像生成配置

    使用统一的 VideoResolution 枚举获取宽高参数。
    """
    width: int
    height: int
    num_inference_steps: int = 30
    lora_name: Optional[str] = None
    lora_weight: float = 1.2
    topic_prefix: str = ""

    @classmethod
    def for_landscape(cls) -> "GenerationConfig":
        """创建横屏配置（使用统一的 VideoResolution）"""
        resolution = VideoResolution.HD_LANDSCAPE
        return cls(width=resolution.width, height=resolution.height)

    @classmethod
    def for_portrait(cls) -> "GenerationConfig":
        """创建竖屏配置（使用统一的 VideoResolution）"""
        resolution = VideoResolution.HD_PORTRAIT
        return cls(width=resolution.width, height=resolution.height)

    @classmethod
    def for_resolution(cls, resolution: VideoResolution) -> "GenerationConfig":
        """根据指定分辨率创建配置

        Args:
            resolution: VideoResolution 枚举值

        Returns:
            GenerationConfig: 生成配置实例
        """
        return cls(width=resolution.width, height=resolution.height)

    def swap_dimensions(self) -> "GenerationConfig":
        """交换宽度和高度"""
        return GenerationConfig(
            width=self.height,
            height=self.width,
            num_inference_steps=self.num_inference_steps,
            lora_name=self.lora_name,
            lora_weight=self.lora_weight,
            topic_prefix=self.topic_prefix,
        )

# ============================================================================
# 图像生成步骤
# ============================================================================

class ImageGenerationStep(BaseStep):
    """图像生成步骤

    功能:
    1. 为每个分镜生成图像
    2. 使用 IImageGenerationService 实现并发生成
    3. 支持多个图像生成服务（通过依赖注入）

    输入 (context/kwargs):
    - splits: 分镜数据
    - workspace_dir: 工作目录
    - topic_prompts: 话题提示词配置
    - is_horizontal: 横竖屏标志
    - loras: LoRA 配置

    输出 (ImageResult):
    - image_paths: 生成的图像路径列表
    - selected_images: 用户选择的图像列表
    - generation_time: 总生成时间
    - parallel_count: 并行任务数

    依赖注入:
    - 通过 __init__ 接收 IImageGenerationService 实例
    - 如果未提供，使用默认的 CeleryImageService

    注意:
    - 此步骤不包含应用层重试逻辑
    - 重试由 Celery 任务级重试机制处理 (process_video_job)
    - 图像生成任务失败时，整个 Pipeline 会失败并由 Celery 重试
    """

    name = "ImageGeneration"
    description = "AI 图像生成（使用服务层并行）"

    # 启用函数式模式
    _functional_mode = True

    def __init__(self, image_service: Optional[IImageGenerationService] = None):
        """初始化图像生成步骤

        Args:
            image_service: 图像生成服务实例（可选）
                           如果不提供，将创建默认的 CeleryImageService
        """
        if image_service is None:
            from core.clients.celery_image_service import CeleryImageService
            image_service = CeleryImageService()

        self.image_service = image_service

    def validate(self, context: PipelineContext) -> None:
        """验证输入"""
        splits = getattr(context, 'splits', None)
        if not splits:
            raise ValueError("没有分镜数据")

        if not context.workspace_dir:
            raise ValueError("工作目录未设置")

    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行图像生成（传统模式）

        此方法保持向后兼容，内部调用函数式模式。
        """
        # 调用函数式实现
        result = self._execute_functional(context)

        # 将结果合并到 context
        context.image_paths = result.data.get("image_paths")
        context.selected_images = result.data.get("selected_images")

        return context

    def _execute_functional(
        self,
        context: PipelineContext,
        **kwargs
    ) -> "ImageResult":
        """执行图像生成（函数式模式）

        使用注入的 IImageGenerationService 实现并行图片生成。

        Args:
            context: Pipeline 上下文
            **kwargs: 额外参数，可以包含 splits

        Returns:
            ImageResult: 包含 image_paths, selected_images 的结果
        """
        from ..results import ImageResult

        splits = self._get_splits(context, kwargs)
        images_dir = self._prepare_output_directory(context.workspace_dir)
        config = self._build_generation_config(context)
        generation_params = self._prepare_generation_params(
            splits, images_dir, config
        )

        # 执行并行生成（通过依赖注入的服务）
        service_results = self.image_service.generate_batch(
            generation_params=generation_params,
            job_id=context.job_id,
        )

        # 收集结果
        result_summary = self._collect_service_results(service_results, len(splits))
        generation_time = time.time() - result_summary.start_time

        self._log_generation_completion(
            context.job_id, result_summary, generation_time
        )

        return ImageResult(
            step_name=self.name,
            image_paths=result_summary.image_paths,
            selected_images=result_summary.image_paths,
            generation_time=generation_time,
            parallel_count=len(splits),
        )

    # ========================================================================
    # 辅助方法 - 单一职责
    # ========================================================================

    def _get_splits(self, context: PipelineContext, kwargs: Dict) -> List[Dict]:
        """获取分镜数据

        Args:
            context: Pipeline 上下文
            kwargs: 额外参数

        Returns:
            List[Dict]: 分镜数据列表

        Raises:
            ValueError: 如果没有 splits 参数
        """
        splits = kwargs.get("splits")
        if not splits:
            splits = getattr(context, 'splits', None)

        if not splits:
            raise ValueError("需要 splits 参数")

        return splits

    def _prepare_output_directory(self, workspace_dir: str) -> Path:
        """准备输出目录

        Args:
            workspace_dir: 工作目录路径

        Returns:
            Path: 图像输出目录
        """
        images_dir = Path(workspace_dir) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    def _build_generation_config(self, context: PipelineContext) -> GenerationConfig:
        """构建生成配置

        Args:
            context: Pipeline 上下文

        Returns:
            GenerationConfig: 生成配置对象
        """
        # 根据横竖屏选择基础配置
        config = (
            GenerationConfig.for_landscape()
            if context.is_horizontal
            else GenerationConfig.for_portrait()
        )

        # 添加 LoRA 配置
        loras = context.loras or []
        if loras:
            config.lora_name = loras[0].get("name")
            config.lora_weight = loras[0].get("weight", 1.2)

        # 添加话题前缀
        if context.topic_prompts:
            config.topic_prefix = context.topic_prompts.get("prompt_gen_images", "")

        return config

    def _prepare_generation_params(
        self,
        splits: List[Dict],
        images_dir: Path,
        config: GenerationConfig
    ) -> List[Dict[str, Any]]:
        """准备生成参数列表

        Args:
            splits: 分镜数据列表
            images_dir: 输出目录
            config: 生成配置

        Returns:
            List[Dict[str, Any]]: 生成参数列表
        """
        generation_params = []

        for split in splits:
            params = {
                "prompt": split.get("prompt", split["text"]),
                "output_path": str(images_dir / f"split_{split['index']:03d}.png"),
                "width": config.width,
                "height": config.height,
                "num_inference_steps": config.num_inference_steps,
                "lora_name": config.lora_name,
                "lora_weight": config.lora_weight,
                "topic_prefix": config.topic_prefix,
            }
            generation_params.append(params)

        return generation_params

    @dataclass
    class ResultSummary:
        """结果摘要"""
        image_paths: List[str]
        success_count: int
        failed_count: int
        start_time: float

    def _collect_service_results(
        self,
        service_results: List,
        total_count: int
    ) -> ResultSummary:
        """收集服务结果

        Args:
            service_results: ImageGenerationResult 列表
            total_count: 总任务数

        Returns:
            ResultSummary: 结果摘要
        """
        from core.interfaces.service_interfaces import ImageGenerationResult

        image_paths = []
        success_count = 0
        failed_count = 0

        for result in service_results:
            image_paths.append(result.output_path)
            if result.status == "success":
                success_count += 1
            else:
                failed_count += 1
                logger.warning(
                    f"[{self.name}] 图片生成失败: {result.output_path}, "
                    f"error={result.error_message}"
                )

        return self.ResultSummary(
            image_paths=image_paths,
            success_count=success_count,
            failed_count=failed_count,
            start_time=time.time(),
        )

    def _log_generation_completion(
        self,
        job_id: int,
        summary: ResultSummary,
        generation_time: float
    ) -> None:
        """记录生成完成日志

        Args:
            job_id: 任务 ID
            summary: 结果摘要
            generation_time: 生成时间
        """
        logger.info(
            f"[{self.name}] 图像生成完成 "
            f"(job_id={job_id}, 成功={summary.success_count}/{summary.success_count + summary.failed_count}, "
            f"失败={summary.failed_count}, 耗时={generation_time:.2f}秒)"
        )

    def _create_placeholder_image(
        self,
        output_dir: Path,
        index: int,
        error_msg: str = ""
    ) -> str:
        """创建占位图像

        Args:
            output_dir: 输出目录
            index: 分镜索引
            error_msg: 错误信息

        Returns:
            str: 占位图像路径
        """
        from PIL import Image, ImageDraw, ImageFont

        output_path = output_dir / f"split_{index:03d}.png"

        # 使用统一的 VideoResolution 获取默认尺寸
        resolution = VideoResolution.HD_LANDSCAPE
        img = Image.new("RGB", (resolution.width, resolution.height), color=(40, 40, 40))
        draw = ImageDraw.Draw(img)

        # 加载字体
        font = self._load_font()

        # 添加文本
        text_display = f"分镜 {index + 1}"
        if error_msg:
            text_display = f"{text_display}: {error_msg[:50]}"

        draw.text((resolution.width // 2, resolution.height // 2), text_display, fill="white", font=font, anchor="mm")
        img.save(output_path)

        logger.debug(f"[{self.name}] 占位图像已创建: {output_path}")
        return str(output_path)

    def _load_font(self) -> Any:
        """加载字体

        Returns:
            ImageFont: 字体对象
        """
        from PIL import ImageFont

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "arial.ttf",
        ]

        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, 40)
            except Exception:
                continue

        return ImageFont.load_default()

    def _context_to_result(self, context: PipelineContext) -> "ImageResult":
        """将 PipelineContext 转换为 ImageResult

        Args:
            context: Pipeline 上下文

        Returns:
            ImageResult
        """
        from ..results import ImageResult

        image_paths = getattr(context, 'image_paths', [])
        selected_images = getattr(context, 'selected_images', image_paths.copy())

        return ImageResult(
            step_name=self.name,
            image_paths=image_paths,
            selected_images=selected_images,
            generation_time=0.0,
            parallel_count=0,
        )


__all__ = [
    "ImageGenerationStep",
    "GenerationConfig",
    # VideoResolution 现在从 core.config.video_config 导入
    # 为了向后兼容，可以从这里重新导出
]

# 向后兼容：重新导出 VideoResolution
from core.config.video_config import VideoResolution
__all__.append("VideoResolution")

