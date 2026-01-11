"""数据模型模块."""

from .schemas import (
    ASRRequest,
    ASRResponse,
    SentenceInfo,
    TTSRequest,
    TTSResponse,
)

__all__ = [
    "SentenceInfo",
    "TTSRequest",
    "TTSResponse",
    "ASRRequest",
    "ASRResponse",
]

