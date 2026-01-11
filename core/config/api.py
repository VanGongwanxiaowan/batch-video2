"""API 端点和配置文件路径常量

提供统一的 API 端点定义和配置文件路径，替换硬编码的路径字符串。

代码重构说明：
- 将 API 端点路径集中管理
- 提供配置文件路径常量
- 支持版本化 API
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class APIEndpoint:
    """API 端点定义

    Args:
        path: 端点路径（不含版本前缀和前导斜杠）
        method: HTTP 方法（默认 GET）
        version: API 版本（默认 v1）
    """
    path: str
    method: str = "GET"
    version: str = "v1"

    @property
    def full_path(self) -> str:
        """获取完整路径（包含版本前缀）

        Returns:
            str: 完整的 API 路径，如 /api/v1/jobs
        """
        return f"/api/{self.version}/{self.path}"


class APIEndpoints:
    """API 端点常量

    集中管理所有 API 端点路径。

    示例:
        >>> endpoint = APIEndpoints.JOB_CREATE
        >>> endpoint.method
        'POST'
        >>> endpoint.full_path
        '/api/v1/jobs'
    """

    # Job 相关端点
    JOB_LIST = APIEndpoint("jobs", "GET")
    JOB_CREATE = APIEndpoint("jobs", "POST")
    JOB_DETAIL = APIEndpoint("jobs/{id}", "GET")
    JOB_UPDATE = APIEndpoint("jobs/{id}", "PUT")
    JOB_DELETE = APIEndpoint("jobs/{id}", "DELETE")
    JOB_SUBMIT = APIEndpoint("jobs/{id}/submit", "POST")
    JOB_CANCEL = APIEndpoint("jobs/{id}/cancel", "POST")

    # Account 相关端点
    ACCOUNT_LIST = APIEndpoint("accounts", "GET")
    ACCOUNT_CREATE = APIEndpoint("accounts", "POST")
    ACCOUNT_DETAIL = APIEndpoint("accounts/{id}", "GET")
    ACCOUNT_UPDATE = APIEndpoint("accounts/{id}", "PUT")
    ACCOUNT_DELETE = APIEndpoint("accounts/{id}", "DELETE")

    # Voice 相关端点
    VOICE_LIST = APIEndpoint("voices", "GET")
    VOICE_CREATE = APIEndpoint("voices", "POST")
    VOICE_DETAIL = APIEndpoint("voices/{id}", "GET")
    VOICE_UPDATE = APIEndpoint("voices/{id}", "PUT")
    VOICE_DELETE = APIEndpoint("voices/{id}", "DELETE")

    # Language 相关端点
    LANGUAGE_LIST = APIEndpoint("languages", "GET")
    LANGUAGE_CREATE = APIEndpoint("languages", "POST")
    LANGUAGE_DETAIL = APIEndpoint("languages/{id}", "GET")
    LANGUAGE_UPDATE = APIEndpoint("languages/{id}", "PUT")
    LANGUAGE_DELETE = APIEndpoint("languages/{id}", "DELETE")

    # Topic 相关端点
    TOPIC_LIST = APIEndpoint("topics", "GET")
    TOPIC_CREATE = APIEndpoint("topics", "POST")
    TOPIC_DETAIL = APIEndpoint("topics/{id}", "GET")
    TOPIC_UPDATE = APIEndpoint("topics/{id}", "PUT")
    TOPIC_DELETE = APIEndpoint("topics/{id}", "DELETE")

    # Job Split 相关端点
    JOB_SPLIT_LIST = APIEndpoint("job_splits", "GET")
    JOB_SPLIT_CREATE = APIEndpoint("job_splits", "POST")
    JOB_SPLIT_DETAIL = APIEndpoint("job_splits/{id}", "GET")
    JOB_SPLIT_UPDATE = APIEndpoint("job_splits/{id}", "PUT")
    JOB_SPLIT_DELETE = APIEndpoint("job_splits/{id}", "DELETE")

    # 文件相关端点
    FILE_UPLOAD = APIEndpoint("files/upload", "POST")
    FILE_DOWNLOAD = APIEndpoint("files/{id}", "GET")
    FILE_DELETE = APIEndpoint("files/{id}", "DELETE")

    # 任务相关端点
    TASK_STATUS = APIEndpoint("tasks/{id}", "GET")
    TASK_LIST = APIEndpoint("tasks", "GET")
    TASK_CANCEL = APIEndpoint("tasks/{id}/cancel", "POST")

    # 数字人相关端点
    DIGITAL_HUMAN_GENERATE = APIEndpoint("human/generate", "POST")
    DIGITAL_HUMAN_STATUS = APIEndpoint("human/status/{id}", "GET")
    DIGITAL_HUMAN_VIDEO = APIEndpoint("human/video/{id}", "GET")


class ConfigFilePaths:
    """配置文件路径常量

    集中管理所有配置文件的文件名和相对路径。

    示例:
        >>> ConfigFilePaths.HUMAN_CONFIG
        'human_config.json'
        >>> ConfigFilePaths.get_font_path("方正粗谭黑简体.ttf")
        'fonts/方正粗谭黑简体.ttf'
    """

    # 配置文件名
    HUMAN_CONFIG = "human_config.json"
    TTS_CONFIG = "tts_config.json"
    IMAGE_CONFIG = "image_config.json"
    TOPIC_CONFIG = "topic_config.json"
    VIDEO_CONFIG = "video_config.json"

    # OpenCC 繁简转换配置文件
    OPENCC_S2T_CONFIG = "s2t.json"  # 简体转繁体
    OPENCC_T2S_CONFIG = "t2s.json"  # 繁体转简体

    # 相对路径常量
    FONTS_DIR = "fonts"
    BACKGROUNDS_DIR = "backgrounds"
    TEMPLATES_DIR = "templates"
    LOGOS_DIR = "logos"

    @staticmethod
    def get_font_path(font_name: str) -> str:
        """获取字体文件路径

        Args:
            font_name: 字体文件名

        Returns:
            str: 字体文件的相对路径
        """
        return f"{ConfigFilePaths.FONTS_DIR}/{font_name}"

    @staticmethod
    def get_background_path(bg_name: str) -> str:
        """获取背景图片路径

        Args:
            bg_name: 背景图片文件名

        Returns:
            str: 背景图片的相对路径
        """
        return f"{ConfigFilePaths.BACKGROUNDS_DIR}/{bg_name}"

    @staticmethod
    def get_logo_path(logo_name: str) -> str:
        """获取 Logo 文件路径

        Args:
            logo_name: Logo 文件名

        Returns:
            str: Logo 文件的相对路径
        """
        return f"{ConfigFilePaths.LOGOS_DIR}/{logo_name}"


class ServiceURLs:
    """服务 URL 常量

    集中管理各个服务的 URL 配置。
    """

    # 图像生成服务
    AI_IMAGE_GEN_SERVICE = "AI_IMAGE_GEN_API_URL"
    AI_IMAGE_GEN_DEFAULT = "http://localhost:8000"

    # TTS 服务
    AZURE_TTS_SERVICE = "AZURE_TTS_API_URL"
    AZURE_TTS_DEFAULT = "http://localhost:8001"

    # SeedVC TTS 服务
    SEEDVC_TTS_SERVICE = "SEEDVC_TTS_API_URL"
    SEEDVC_TTS_DEFAULT = "http://localhost:8002"

    # Flux 图像生成服务
    FLUX_SERVICE = "FLUX_API_URL"
    FLUX_DEFAULT = "http://localhost:8003"

    # 数字人服务
    HUMAN_SERVICE = "HUMAN_SERVICE_URL"
    HUMAN_DEFAULT = "http://localhost:8004"


class OSSStoragePaths:
    """OSS 存储路径常量

    集中管理 OSS 上的文件路径前缀和命名规范。
    """

    # 主要路径前缀
    VIDEO_PREFIX = "videos"
    IMAGE_PREFIX = "images"
    AUDIO_PREFIX = "audio"
    SUBTITLE_PREFIX = "subtitles"
    TEMP_PREFIX = "temp"

    # 文件命名模板
    VIDEO_FILENAME = "final.mp4"
    COVER_FILENAME = "cover.png"
    AUDIO_FILENAME = "audio.mp3"
    SUBTITLE_FILENAME = "subtitle.srt"


class SubtitleStyleConfig:
    """字幕样式配置常量

    集中管理字幕样式相关的配置，消除硬编码的样式值。
    """

    # 字体配置
    DEFAULT_FONT = "微软雅黑"
    DEFAULT_FONT_SIZE = 48
    DEFAULT_FONT_COLOR = "white"
    DEFAULT_OUTLINE_COLOR = "black"

    # 颜色映射（FFmpeg ASS 格式使用 BGR 格式）
    COLOR_MAP = {
        "white": "FFFFFF",
        "black": "000000",
        "red": "0000FF",  # BGR 格式
        "yellow": "00FFFF",
        "blue": "FF0000",
        "green": "00FF00",
    }

    # FFmpeg 输出标签
    FFMPEG_OUTPUT_LABEL = "[out]"

    # Logo 尺寸
    LOGO_SCALE_WIDTH = 100

    @classmethod
    def color_to_hex(cls, color_name: str) -> str:
        """颜色名称转十六进制

        Args:
            color_name: 颜色名称

        Returns:
            str: 十六进制颜色值
        """
        return cls.COLOR_MAP.get(color_name.lower(), "FFFFFF")


class TextProcessingConfig:
    """文本处理配置常量

    集中管理文本处理相关的配置。
    """

    # 分隔符
    DOUBLE_NEWLINE = "\n\n"
    SINGLE_NEWLINE = "\n"
    DOUBLE_SPACE = "  "

    # 最大长度
    MAX_SPLIT_TEXT_LENGTH = 100


# 便捷函数
def get_endpoint_url(endpoint: APIEndpoint, base_url: str = "", **params) -> str:
    """获取完整的 API 端点 URL

    Args:
        endpoint: API 端点定义
        base_url: 基础 URL（可选）
        **params: 路径参数，如 id=123

    Returns:
        str: 完整的 URL

    Examples:
        >>> get_endpoint_url(APIEndpoints.JOB_DETAIL, id=123)
        '/api/v1/jobs/123'
        >>> get_endpoint_url(APIEndpoints.JOB_DETAIL, "http://example.com", id=123)
        'http://example.com/api/v1/jobs/123'
    """
    path = endpoint.full_path
    for key, value in params.items():
        path = path.replace(f"{{{key}}}", str(value))
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return path


__all__ = [
    "APIEndpoint",
    "APIEndpoints",
    "ConfigFilePaths",
    "ServiceURLs",
    "OSSStoragePaths",
    "SubtitleStyleConfig",
    "TextProcessingConfig",
    "get_endpoint_url",
]
