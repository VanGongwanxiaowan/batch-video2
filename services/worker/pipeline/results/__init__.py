"""Pipeline 步骤结果类型定义

This package defines result types returned by pipeline steps.
Each module contains related result types organized by domain.

Using explicit result types instead of mutating PipelineContext provides:
- Type safety: Clear input/output types
- Testability: Easy to test individual steps
- Data flow clarity: Explicit dependencies between steps
- Decoupling: Steps don't need to know about context structure
"""

# 导出所有结果类型
from .base import StepResult, StepError, StepResultType
from .tts import TTSResult
from .subtitle import SubtitleResult
from .split import SplitResult
from .image import ImageResult
from .video import VideoResult, DigitalHumanResult
from .postprocess import PostProcessResult
from .upload import UploadResult

__all__ = [
    # Base result type
    "StepResult",
    "StepError",
    "StepResultType",
    # Specific result types
    "TTSResult",
    "SubtitleResult",
    "SplitResult",
    "ImageResult",
    "VideoResult",
    "DigitalHumanResult",
    "PostProcessResult",
    "UploadResult",
]
