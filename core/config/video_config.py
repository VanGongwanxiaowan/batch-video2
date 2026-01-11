"""视频处理配置

统一管理视频分辨率、编码参数、FFmpeg 设置等配置，
消除代码中的魔法数字和硬编码值。

创建日期: 2024年重构
目的: 替换散落在各文件中的 1360x768 硬编码
"""
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ============================================================================
# 视频分辨率枚举 - 统一所有分辨率常量
# ============================================================================


class VideoResolution(Enum):
    """标准视频分辨率预设

    替代硬编码的 (1360, 768) 等魔法数字。
    支持横屏、竖屏、标准分辨率等多种格式。

    使用示例:
        resolution = VideoResolution.HD_LANDSCAPE
        width, height = resolution.value
        # 或者
        width = resolution.width
        height = resolution.height
    """

    # ========== HD 分辨率 (当前项目默认) ==========
    HD_LANDSCAPE = (1360, 768)   # 16:9 横屏 (项目默认)
    HD_PORTRAIT = (768, 1360)    # 9:16 竖屏 (项目默认)

    # ========== 标准高清分辨率 ==========
    SD_480P = (854, 480)         # 16:9 标清
    HD_720P = (1280, 720)        # 16:9 720p
    FULL_HD_1080P = (1920, 1080) # 16:9 1080p
    QHD_1440P = (2560, 1440)     # 16:9 1440p
    UHD_4K = (3840, 2160)        # 16:9 4K

    # ========== 社交媒体分辨率 ==========
    SQUARE = (1080, 1080)         # 1:1 正方形
    INSTAGRAM_PORTRAIT = (1080, 1350)  # 4:5 Instagram
    TIKTOK_PORTRAIT = (1080, 1920)     # 9:16 TikTok
    SNAPCHAT_VERTICAL = (1080, 1920)   # 9:16 Snapchat

    # ========== 移动设备分辨率 ==========
    MOBILE_HD = (720, 1280)      # 9:16 移动 HD
    MOBILE_FHD = (1080, 1920)    # 9:16 移动 FHD

    @property
    def width(self) -> int:
        """获取宽度"""
        return self.value[0]

    @property
    def height(self) -> int:
        """获取高度"""
        return self.value[1]

    @property
    def aspect_ratio(self) -> float:
        """获取宽高比

        Returns:
            float: 宽高比 (width / height)
        """
        return self.width / self.height

    @property
    def aspect_ratio_str(self) -> str:
        """获取宽高比字符串表示

        Returns:
            str: 如 "16:9", "9:16"
        """
        # 计算最简分数
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        divisor = gcd(self.width, self.height)
        w = self.width // divisor
        h = self.height // divisor
        return f"{w}:{h}"

    def is_landscape(self) -> bool:
        """是否为横屏"""
        return self.width > self.height

    def is_portrait(self) -> bool:
        """是否为竖屏"""
        return self.height > self.width

    def is_square(self) -> bool:
        """是否为正方形"""
        return self.width == self.height

    def swap(self) -> "VideoResolution":
        """交换宽度和高度（旋转90度）

        Returns:
            VideoResolution: 旋转后的分辨率

        Raises:
            ValueError: 如果旋转后没有对应的预设
        """
        swapped = (self.height, self.width)
        for resolution in VideoResolution:
            if resolution.value == swapped:
                return resolution
        # 如果没有精确匹配，返回动态创建的值
        return VideoResolution(swapped)

    @classmethod
    def from_dimensions(cls, width: int, height: int) -> "VideoResolution":
        """根据宽高创建或获取分辨率

        Args:
            width: 宽度
            height: 高度

        Returns:
            VideoResolution: 匹配的预设或动态创建的值
        """
        for resolution in cls:
            if resolution.value == (width, height):
                return resolution
        # 如果没有匹配的预设，动态创建
        return cls((width, height))

    @classmethod
    def for_orientation(cls, is_horizontal: bool = True) -> "VideoResolution":
        """根据方向获取默认分辨率

        Args:
            is_horizontal: True 为横屏，False 为竖屏

        Returns:
            VideoResolution: 对应方向的默认 HD 分辨率
        """
        return cls.HD_LANDSCAPE if is_horizontal else cls.HD_PORTRAIT


# ============================================================================
# 视频处理配置 - 统一编码和处理参数
# ============================================================================


@dataclass(frozen=True)
class VideoProcessingConfig:
    """视频处理参数配置

    不可变配置类，防止意外修改。
    包含视频编码、音频编码、转场等所有处理参数。

    使用示例:
        config = VideoProcessingConfig.for_landscape()
        width, height = config.width, config.height

        # 自定义配置
        config = VideoProcessingConfig(
            resolution=VideoResolution.FULL_HD_1080P,
            fps=30,
            duration_per_image=3.0
        )
    """

    # ========== 分辨率相关 ==========
    resolution: VideoResolution = VideoResolution.HD_LANDSCAPE

    # ========== 帧率设置 ==========
    fps: int = 24
    fps_options: Tuple[int, ...] = (24, 25, 30, 50, 60)

    # ========== 视频编码参数 ==========
    video_codec: str = "libx264"
    crf_quality: int = 23  # CRF (0-51, 越低质量越好)
    preset: str = "veryfast"  # 编码速度预设: ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    pix_fmt: str = "yuv420p"  # 像素格式

    # ========== 音频编码参数 ==========
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 48000
    audio_channels: int = 2

    # ========== 转场参数 ==========
    transition_duration: float = 1.0  # 转场持续时间（秒）
    transition_types: Tuple[str, ...] = ("fade", "slide", "zoom", "dissolve")

    # ========== 每张图片持续时间 ==========
    duration_per_image: float = 5.0  # 每张图片的默认持续时间（秒）

    # ========== 字幕相关 ==========
    subtitle_font_size: int = 48
    subtitle_font_color: str = "white"
    subtitle_font_name: str = "Arial"

    # ========== 超时设置 ==========
    ffmpeg_timeout: int = 600  # FFmpeg 执行超时（秒）

    @classmethod
    def for_landscape(cls) -> "VideoProcessingConfig":
        """创建横屏配置（项目默认）"""
        return cls(resolution=VideoResolution.HD_LANDSCAPE)

    @classmethod
    def for_portrait(cls) -> "VideoProcessingConfig":
        """创建竖屏配置（项目默认）"""
        return cls(resolution=VideoResolution.HD_PORTRAIT)

    @classmethod
    def for_resolution(cls, resolution: VideoResolution) -> "VideoProcessingConfig":
        """为特定分辨率创建配置"""
        return cls(resolution=resolution)

    @property
    def width(self) -> int:
        """获取视频宽度"""
        return self.resolution.width

    @property
    def height(self) -> int:
        """获取视频高度"""
        return self.resolution.height

    @property
    def aspect_ratio(self) -> float:
        """获取宽高比"""
        return self.resolution.aspect_ratio

    @property
    def is_landscape(self) -> bool:
        """是否为横屏"""
        return self.resolution.is_landscape()

    @property
    def is_portrait(self) -> bool:
        """是否为竖屏"""
        return self.resolution.is_portrait()


# ============================================================================
# FFmpeg 配置 - 统一 FFmpeg 相关常量
# ============================================================================


class FFmpegConfig:
    """FFmpeg 命令配置常量

    统一 FFmpeg 命令构建中使用的各种常量。
    """

    # ========== 编码预设 ==========
    PRESET_ULTRAFAST = "ultrafast"
    PRESET_SUPERFAST = "superfast"
    PRESET_VERYFAST = "veryfast"  # 默认
    PRESET_FASTER = "faster"
    PRESET_FAST = "fast"
    PRESET_MEDIUM = "medium"
    PRESET_SLOW = "slow"
    PRESET_SLOWER = "slower"
    PRESET_VERYSLOW = "veryslow"

    # ========== CRF 质量值 ==========
    CRF_LOSSLESS = 0      # 无损
    CRF_HIGH_QUALITY = 15  # 高质量
    CRF_GOOD_QUALITY = 18  # 良好质量
    CRF_DEFAULT = 23      # 默认质量 (H.264)
    CRF_MEDIUM = 26       # 中等质量
    CRF_LOW_QUALITY = 30  # 低质量

    # ========== 视频编解码器 ==========
    CODEC_H264 = "libx264"
    CODEC_H265 = "libx265"
    CODEC_VP9 = "libvpx-vp9"
    CODEC_AV1 = "libaom-av1"
    CODEC_COPY = "copy"

    # ========== 音频编解码器 ==========
    AUDIO_CODEC_AAC = "aac"
    AUDIO_CODEC_MP3 = "libmp3lame"
    AUDIO_CODEC_OPUS = "libopus"
    AUDIO_CODEC_VORBIS = "libvorbis"
    AUDIO_CODEC_COPY = "copy"

    # ========== 像素格式 ==========
    PIX_FMT_YUV420P = "yuv420p"  # 最兼容
    PIX_FMT_YUV422P = "yuv422p"
    PIX_FMT_YUV444P = "yuv444p"
    PIX_FMT_RGB24 = "rgb24"

    # ========== 滤镜参数 ==========
    # 字幕位置偏移
    SUBTITLE_X_OFFSET = 10
    SUBTITLE_Y_OFFSET = 10

    # Logo 叠加位置
    LOGO_POSITION_TOP_LEFT = "10:10"
    LOGO_POSITION_TOP_RIGHT = "W-w-10:10"
    LOGO_POSITION_BOTTOM_LEFT = "10:H-h-10"
    LOGO_POSITION_BOTTOM_RIGHT = "W-w-10:H-h-10"
    LOGO_POSITION_CENTER = "(W-w)/2:(H-h)/2"

    # ========== 超时设置 ==========
    DEFAULT_TIMEOUT = 300      # 默认超时（5分钟）
    VIDEO_TIMEOUT = 600        # 视频处理超时（10分钟）
    LONG_TIMEOUT = 1800        # 长时间处理超时（30分钟）


# ============================================================================
# 默认配置实例 - 便捷访问
# ============================================================================

# 横屏默认配置
DEFAULT_LANDSCAPE_CONFIG = VideoProcessingConfig.for_landscape()

# 竖屏默认配置
DEFAULT_PORTRAIT_CONFIG = VideoProcessingConfig.for_portrait()


# ============================================================================
# 便捷函数
# ============================================================================


def get_video_config(is_horizontal: bool = True) -> VideoProcessingConfig:
    """根据方向获取视频配置

    Args:
        is_horizontal: True 为横屏，False 为竖屏

    Returns:
        VideoProcessingConfig: 对应的配置实例
    """
    return DEFAULT_LANDSCAPE_CONFIG if is_horizontal else DEFAULT_PORTRAIT_CONFIG


def get_resolution(is_horizontal: bool = True) -> VideoResolution:
    """根据方向获取分辨率

    Args:
        is_horizontal: True 为横屏，False 为竖屏

    Returns:
        VideoResolution: 对应的分辨率
    """
    return VideoResolution.for_orientation(is_horizontal)


def get_dimensions(is_horizontal: bool = True) -> Tuple[int, int]:
    """根据方向获取宽度和高度

    Args:
        is_horizontal: True 为横屏，False 为竖屏

    Returns:
        Tuple[int, int]: (宽度, 高度)
    """
    resolution = get_resolution(is_horizontal)
    return resolution.width, resolution.height


# ============================================================================
# 向后兼容 - 映射到旧的 constants.py
# ============================================================================

# 为了向后兼容，导出与 constants.py 一致的值
# 这些将在后续重构中逐步替换为使用上述类

DEFAULT_IMAGE_WIDTH = VideoResolution.HD_LANDSCAPE.width
DEFAULT_IMAGE_HEIGHT = VideoResolution.HD_LANDSCAPE.height
DEFAULT_VERTICAL_WIDTH = VideoResolution.HD_PORTRAIT.width
DEFAULT_VERTICAL_HEIGHT = VideoResolution.HD_PORTRAIT.height


__all__ = [
    # 分辨率枚举
    "VideoResolution",
    # 配置类
    "VideoProcessingConfig",
    "FFmpegConfig",
    # 默认实例
    "DEFAULT_LANDSCAPE_CONFIG",
    "DEFAULT_PORTRAIT_CONFIG",
    # 便捷函数
    "get_video_config",
    "get_resolution",
    "get_dimensions",
    # 向后兼容常量
    "DEFAULT_IMAGE_WIDTH",
    "DEFAULT_IMAGE_HEIGHT",
    "DEFAULT_VERTICAL_WIDTH",
    "DEFAULT_VERTICAL_HEIGHT",
]
