"""服务接口模块

包含所有外部服务的抽象接口定义。

遵循依赖倒置原则：
- 高层模块（如 Pipeline 步骤）依赖这些抽象接口
- 低层模块（具体服务实现）实现这些抽象接口

优势：
1. 可以轻松替换服务实现
2. 便于进行单元测试
3. 符合 SOLID 原则
"""

from .service_interfaces import (
    # TTS
    ITTSService,
    TTSResult,
    # Image
    IImageGenerationService,
    ImageGenerationResult,
    # Storage
    IFileStorageService,
    FileUploadResult,
    BatchUploadResult,
    # Video
    IVideoCompositionService,
    VideoCompositionResult,
    # Digital Human
    IDigitalHumanService,
    DigitalHumanResult,
    # Subtitle
    ISubtitleService,
    SubtitleResult,
)
from .step_factory import (
    # Factory
    IStepFactory,
)

__all__ = [
    # TTS
    "ITTSService",
    "TTSResult",
    # Image
    "IImageGenerationService",
    "ImageGenerationResult",
    # Storage
    "IFileStorageService",
    "FileUploadResult",
    "BatchUploadResult",
    # Video
    "IVideoCompositionService",
    "VideoCompositionResult",
    # Digital Human
    "IDigitalHumanService",
    "DigitalHumanResult",
    # Subtitle
    "ISubtitleService",
    "SubtitleResult",
    # Factory
    "IStepFactory",
]
