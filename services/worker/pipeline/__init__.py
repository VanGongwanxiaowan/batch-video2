"""Pipeline 模块

提供可组合的视频生成 Pipeline。
使用策略模式和构建器模式实现灵活的步骤组合。

架构支持：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：execute_functional() 返回 StepResult

传统模式示例:
    ```python
    from services.worker.pipeline import PipelineBuilder, PipelineContext

    # 创建上下文
    context = PipelineContext.from_job(job, db)

    # 构建 Pipeline（传统模式）
    pipeline = PipelineBuilder.build_standard_pipeline(context)

    # 执行（传统模式）
    pipeline.execute()
    ```

函数式模式示例:
    ```python
    from services.worker.pipeline import PipelineBuilder, PipelineContext

    # 创建上下文
    context = PipelineContext.from_job(job, db)

    # 构建 Pipeline（函数式模式）
    pipeline = PipelineBuilder.build_standard_pipeline(context, functional_mode=True)

    # 执行（函数式模式）
    results = pipeline.execute_functional()
    tts_result = results.get("TTSGeneration")
    audio_path = tts_result.audio_path
    ```
"""

# 新的 Pipeline (推荐使用)
from .context import PipelineContext
from .pipeline import PipelineBuilder, PipelineException, VideoPipeline

# 导出所有步骤和结果类型
from .steps import (
    # 基础类
    BaseStep,
    ConditionalStep,
    RetryableStep,
    SkipStepException,
    StepException,
    StepOutput,
    # 步骤结果类型
    DigitalHumanResult,
    ImageResult,
    PostProcessResult,
    SplitResult,
    StepError,
    StepResult,
    SubtitleResult,
    TTSResult,
    UploadResult,
    VideoResult,
    # 具体步骤
    DigitalHumanStep,
    EdgeTTSSubtitleStep,
    ImageGenerationStep,
    PostProcessingStep,
    SubtitleGenerationStep,
    TextSplitStep,
    TTSGenerationStep,
    UploadStep,
    VideoCompositionStep,
)

# 旧的 Pipeline (向后兼容，已废弃)
from .video_pipeline import VideoGenerationPipeline

__all__ = [
    # 新 Pipeline (推荐)
    "PipelineContext",
    "VideoPipeline",
    "PipelineBuilder",
    "PipelineException",
    # 基础类
    "BaseStep",
    "ConditionalStep",
    "RetryableStep",
    "SkipStepException",
    "StepException",
    "StepOutput",
    # 步骤结果类型
    "StepResult",
    "StepError",
    "TTSResult",
    "SubtitleResult",
    "SplitResult",
    "ImageResult",
    "VideoResult",
    "DigitalHumanResult",
    "PostProcessResult",
    "UploadResult",
    # 具体步骤
    "TTSGenerationStep",
    "EdgeTTSSubtitleStep",
    "SubtitleGenerationStep",
    "TextSplitStep",
    "ImageGenerationStep",
    "VideoCompositionStep",
    "DigitalHumanStep",
    "PostProcessingStep",
    "UploadStep",
    # 旧 Pipeline (已废弃)
    "VideoGenerationPipeline",
]
