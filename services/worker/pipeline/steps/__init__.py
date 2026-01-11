"""Pipeline 步骤模块

包含所有视频生成流程的步骤类。
每个步骤都是独立的、可复用的、可组合的。

架构支持：
1. 传统模式（向后兼容）：execute() 返回 PipelineContext
2. 函数式模式（推荐）：_execute_functional() 返回 StepResult
"""

from .base import (
    BaseStep,
    ConditionalStep,
    # RetryableStep,  # 已废弃：使用 Celery 任务级重试代替应用层重试
    SkipStepException,
    StepException,
    StepOutput,
)

# 导出步骤结果类型
from ..results import (
    StepResult,
    StepError,
    TTSResult,
    SubtitleResult,
    SplitResult,
    ImageResult,
    VideoResult,
    DigitalHumanResult,
    PostProcessResult,
    UploadResult,
)

# 导出各个步骤
from .tts_step import TTSGenerationStep, EdgeTTSSubtitleStep
from .subtitle_step import SubtitleGenerationStep
from .split_step import TextSplitStep
from .image_step import ImageGenerationStep
from .video_step import VideoCompositionStep
from .human_step import DigitalHumanStep
from .postprocess_step import PostProcessingStep
from .upload_step import UploadStep

__all__ = [
    # 基础类
    "BaseStep",
    "ConditionalStep",
    # "RetryableStep",  # 已废弃：使用 Celery 任务级重试代替应用层重试
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
]
