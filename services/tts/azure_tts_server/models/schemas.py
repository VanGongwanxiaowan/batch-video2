"""API 请求和响应模型."""

from typing import Optional

from pydantic import BaseModel, Field


class SentenceInfo(BaseModel):
    """句子信息模型."""

    start: int = Field(default=0, description="开始时间(毫秒)")
    end: int = Field(default=0, description="结束时间(毫秒)")
    timestamp: list[list[float]] = Field(
        default_factory=list,
        description="时间戳列表",
    )
    raw_text: str = Field(default="", description="原始文本")
    spk: int = Field(default=-1, description="说话人ID")


class TTSRequest(BaseModel):
    """TTS 请求模型."""

    audio_text: str = Field(..., description="要合成的文本", min_length=1)
    audio_output_path: str = Field(..., description="音频输出路径")
    subtitle_output_path: Optional[str] = Field(
        default=None,
        description="字幕输出路径(可选)",
    )
    voice: str = Field(
        default="zh-CN-XiaoqiuNeural",
        description="语音模型",
    )
    sample_rate: int = Field(
        default=16000,
        description="采样率",
        ge=8000,
        le=48000,
    )
    volume: int = Field(
        default=50,
        description="音量 (0-100)",
        ge=0,
        le=100,
    )
    speech_rate: float = Field(
        default=1.0,
        description="语速倍数",
        gt=0,
    )


class TTSResponse(BaseModel):
    """TTS 响应模型."""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    audio_file: Optional[str] = Field(
        default=None,
        description="生成的音频文件路径",
    )
    subtitle_file: Optional[str] = Field(
        default=None,
        description="生成的字幕文件路径",
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息(如果失败)",
    )


class ASRRequest(BaseModel):
    """ASR 请求模型."""

    audio_path: str = Field(..., description="音频文件路径")
    srt_path: str = Field(..., description="字幕输出路径")
    content: str = Field(..., description="原始文本内容")


class ASRResponse(BaseModel):
    """ASR 响应模型."""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    srt_file: Optional[str] = Field(
        default=None,
        description="生成的字幕文件路径",
    )
    error: Optional[str] = Field(
        default=None,
        description="错误信息(如果失败)",
    )

