"""服务接口抽象

定义所有外部服务的抽象接口，遵循依赖倒置原则。
高层模块应该依赖这些抽象接口，而不是具体实现。

这允许：
1. 轻松替换服务实现
2. 进行单元测试时使用 Mock 对象
3. 符合开放/封闭原则（对扩展开放，对修改关闭）
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# TTS 服务接口
# ============================================================================

@dataclass
class TTSResult:
    """TTS 合成结果"""
    success: bool
    audio_path: Optional[str] = None
    srt_path: Optional[str] = None
    duration: float = 0.0
    error_message: Optional[str] = None


class ITTSService(ABC):
    """TTS 服务抽象接口

    定义 TTS 语音合成服务的标准接口。
    任何 TTS 实现（Edge TTS, Azure TTS, Google TTS 等）都应该实现此接口。
    """

    @abstractmethod
    def synthesize(
        self,
        text: str,
        language: str,
        output_path: str,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        **kwargs
    ) -> TTSResult:
        """同步合成语音

        Args:
            text: 要合成的文本
            language: 语言代码
            output_path: 输出音频文件路径
            voice: 音色名称
            volume: 音量 (0-100)
            speech_rate: 语速
            **kwargs: 其他参数

        Returns:
            TTSResult: 合成结果
        """
        pass

    @abstractmethod
    async def synthesize_async(
        self,
        text: str,
        language: str,
        output_path: str,
        voice: Optional[str] = None,
        volume: int = 50,
        speech_rate: float = 1.0,
        **kwargs
    ) -> TTSResult:
        """异步合成语音

        Args:
            text: 要合成的文本
            language: 语言代码
            output_path: 输出音频文件路径
            voice: 音色名称
            volume: 音量 (0-100)
            speech_rate: 语速
            **kwargs: 其他参数

        Returns:
            TTSResult: 合成结果
        """
        pass


# ============================================================================
# 图像生成服务接口
# ============================================================================

@dataclass
class ImageGenerationResult:
    """图像生成结果"""
    output_path: str
    status: str  # success, failed
    error_message: Optional[str] = None
    generation_time: float = 0.0


class IImageGenerationService(ABC):
    """图像生成服务抽象接口

    定义图像生成服务的标准接口。
    支持 AI 图像生成（Flux, Stable Diffusion 等）。
    """

    @abstractmethod
    def generate_single_image(
        self,
        prompt: str,
        output_path: str,
        width: int,
        height: int,
        num_inference_steps: int = 30,
        lora_name: Optional[str] = None,
        lora_weight: float = 1.2,
        **kwargs
    ) -> ImageGenerationResult:
        """生成单张图像

        Args:
            prompt: 图像生成提示词
            output_path: 输出文件路径
            width: 图像宽度
            height: 图像高度
            num_inference_steps: 推理步数
            lora_name: LoRA 模型名称
            lora_weight: LoRA 权重
            **kwargs: 其他参数

        Returns:
            ImageGenerationResult: 生成结果
        """
        pass

    @abstractmethod
    def generate_batch(
        self,
        generation_params: List[Dict[str, Any]],
        job_id: int
    ) -> List[ImageGenerationResult]:
        """批量生成图像

        Args:
            generation_params: 生成参数列表
            job_id: 任务 ID

        Returns:
            List[ImageGenerationResult]: 生成结果列表
        """
        pass


# ============================================================================
# 文件存储服务接口
# ============================================================================

@dataclass
class FileUploadResult:
    """文件上传结果"""
    success: bool
    file_key: str  # OSS 上的 key
    url: Optional[str] = None  # 公网访问 URL
    error_message: Optional[str] = None


@dataclass
class BatchUploadResult:
    """批量上传结果"""
    results: Dict[str, FileUploadResult]  # 文件类型 -> 上传结果
    total_size: int = 0  # 总字节数
    success_count: int = 0
    failed_count: int = 0


class IFileStorageService(ABC):
    """文件存储服务抽象接口

    定义文件存储服务的标准接口。
    支持 OSS、S3、本地存储等存储方式。
    """

    @abstractmethod
    def upload_file(
        self,
        file_path: str,
        key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> FileUploadResult:
        """上传单个文件

        Args:
            file_path: 本地文件路径
            key: 存储的 key
            metadata: 元数据

        Returns:
            FileUploadResult: 上传结果
        """
        pass

    @abstractmethod
    def upload_batch(
        self,
        files: Dict[str, str],  # 文件类型 -> 文件路径
        prefix: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchUploadResult:
        """批量上传文件

        Args:
            files: 文件字典 {文件类型: 文件路径}
            prefix: key 前缀
            metadata: 元数据

        Returns:
            BatchUploadResult: 批量上传结果
        """
        pass

    @abstractmethod
    def get_download_url(
        self,
        key: str,
        expires_in: int = 3600
    ) -> Optional[str]:
        """获取下载 URL

        Args:
            key: 文件 key
            expires_in: 过期时间（秒）

        Returns:
            Optional[str]: 下载 URL，如果不支持返回 None
        """
        pass

    @abstractmethod
    def delete_file(self, key: str) -> bool:
        """删除文件

        Args:
            key: 文件 key

        Returns:
            bool: 是否删除成功
        """
        pass


# ============================================================================
# 视频处理服务接口
# ============================================================================

@dataclass
class VideoCompositionResult:
    """视频合成结果"""
    video_path: str
    duration: float
    width: int
    height: int
    segment_count: int
    error_message: Optional[str] = None


class IVideoCompositionService(ABC):
    """视频合成服务抽象接口

    定义视频合成服务的标准接口。
    负责将图像和音频合成为视频。
    """

    @abstractmethod
    def compose_video(
        self,
        image_paths: List[str],
        audio_path: str,
        output_path: str,
        fps: int = 24,
        transition: Optional[str] = None,
        **kwargs
    ) -> VideoCompositionResult:
        """合成视频

        Args:
            image_paths: 图像路径列表
            audio_path: 音频文件路径
            output_path: 输出视频路径
            fps: 帧率
            transition: 转场效果
            **kwargs: 其他参数

        Returns:
            VideoCompositionResult: 合成结果
        """
        pass


# ============================================================================
# 数字人服务接口
# ============================================================================

@dataclass
class DigitalHumanResult:
    """数字人合成结果"""
    success: bool
    video_path: Optional[str] = None
    duration: float = 0.0
    error_message: Optional[str] = None


class IDigitalHumanService(ABC):
    """数字人服务抽象接口

    定义数字人合成服务的标准接口。
    """

    @abstractmethod
    def synthesize(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        config: Dict[str, Any],
        **kwargs
    ) -> DigitalHumanResult:
        """合成数字人视频

        Args:
            video_path: 原始视频路径
            audio_path: 音频文件路径
            output_path: 输出视频路径
            config: 数字人配置
            **kwargs: 其他参数

        Returns:
            DigitalHumanResult: 合成结果
        """
        pass


# ============================================================================
# 字幕生成服务接口
# ============================================================================

@dataclass
class SubtitleResult:
    """字幕生成结果"""
    success: bool
    srt_path: Optional[str] = None
    subtitle_count: int = 0
    error_message: Optional[str] = None


class ISubtitleService(ABC):
    """字幕生成服务抽象接口

    定义字幕生成服务的标准接口。
    """

    @abstractmethod
    def generate_from_audio(
        self,
        audio_path: str,
        output_path: str,
        **kwargs
    ) -> SubtitleResult:
        """从音频生成字幕

        Args:
            audio_path: 音频文件路径
            output_path: 输出字幕文件路径
            **kwargs: 其他参数

        Returns:
            SubtitleResult: 生成结果
        """
        pass


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
]
