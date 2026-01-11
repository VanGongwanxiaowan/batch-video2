"""Azure TTS Server 配置管理."""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.config.settings import BaseConfig


class AzureTTSConfig(BaseConfig):
    """Azure TTS 服务配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # Azure Speech 配置
    AZURE_SPEECH_KEY: str = Field(
        ...,
        description="Azure Speech 服务订阅密钥",
        min_length=1,
    )
    AZURE_SERVICE_REGION: str = Field(
        default="koreacentral",
        description="Azure Speech 服务区域",
    )
    AZURE_SPEECH_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Azure Speech 服务自定义端点 (可选)",
    )

    # 应用配置
    APP_NAME: str = Field(default="Azure TTS Server", description="应用名称")
    APP_VERSION: str = Field(default="1.0.0", description="应用版本")
    DEBUG: bool = Field(default=False, description="调试模式")
    HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    PORT: int = Field(default=6016, description="服务监听端口", ge=1, le=65535)
    CORS_ORIGINS: Optional[str] = Field(
        default=None,
        description="CORS允许的来源（逗号分隔，如：http://localhost:3000,https://example.com）",
    )

    # TTS 默认配置
    DEFAULT_VOICE: str = Field(
        default="zh-CN-XiaoxiaoNeural",
        description="默认语音模型",
    )
    DEFAULT_SAMPLE_RATE: int = Field(
        default=16000,
        description="默认采样率",
    )
    DEFAULT_VOLUME: int = Field(
        default=50,
        description="默认音量 (0-100)",
        ge=0,
        le=100,
    )
    DEFAULT_SPEECH_RATE: float = Field(
        default=1.0,
        description="默认语速倍数",
        gt=0,
    )
    DEFAULT_CHUNK_SIZE: int = Field(
        default=1500,
        description="文本分块默认大小",
        gt=0,
    )

    # ASR 模型配置
    ASR_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="ASR 模型路径",
    )
    ASR_VAD_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="ASR VAD 模型路径",
    )
    ASR_PUNC_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="ASR 标点模型路径",
    )
    ASR_SPK_MODEL_PATH: Optional[str] = Field(
        default=None,
        description="ASR 说话人模型路径",
    )
    ASR_DEVICE: str = Field(
        default="cuda:0",
        description="ASR 模型运行设备",
    )

    # 字幕配置
    SUBTITLE_MAX_CHARS_SQUARE: int = Field(
        default=13,
        description="方块字字幕最大字符数",
    )
    SUBTITLE_MAX_CHARS_NON_SQUARE: int = Field(
        default=24,
        description="非方块字字幕最大字符数",
    )
    SUBTITLE_GAP_SECONDS: float = Field(
        default=0.1,
        description="字幕间隔时间(秒)",
    )

    @field_validator("AZURE_SPEECH_KEY")
    @classmethod
    def validate_speech_key(cls, v: str) -> str:
        """验证 Azure Speech Key 不为空."""
        if not v or not v.strip():
            raise ValueError("AZURE_SPEECH_KEY 不能为空")
        return v.strip()

    @property
    def asr_model_paths(self) -> dict[str, str]:
        """获取 ASR 模型路径配置."""
        return {
            "model": self.ASR_MODEL_PATH
            or "/root/.cache/modelscope/hub/iic/speech_paraformer-large-vad-punc-spk_asr_nat-zh-cn",
            "vad_model": self.ASR_VAD_MODEL_PATH
            or "/root/.cache/modelscope/hub/iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
            "punc_model": self.ASR_PUNC_MODEL_PATH
            or "/root/.cache/modelscope/hub/iic/punc_ct-transformer_cn-en-common-vocab471067-large",
            "spk_model": self.ASR_SPK_MODEL_PATH
            or "/root/.cache/modelscope/hub/iic/speech_campplus_sv_zh-cn_16k-common",
        }

    @property
    def cors_origins_list(self) -> list[str]:
        """获取 CORS 来源列表."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_azure_tts_config() -> AzureTTSConfig:
    """获取缓存的 Azure TTS 配置."""
    return AzureTTSConfig()

