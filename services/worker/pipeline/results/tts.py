"""TTS 步骤结果类型

Result types for text-to-speech generation steps.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import StepResult


@dataclass
class TTSResult(StepResult):
    """Result from TTS generation step.

    Contains:
    - audio_path: Path to generated audio file
    - srt_path: Path to generated subtitle file
    - duration: Audio duration in seconds
    """

    _default_step_name: str = "TTSGeneration"

    audio_path: Optional[str] = None
    srt_path: Optional[str] = None
    duration: Optional[float] = None

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields (skips None values)
        self._auto_populate_data({
            'audio_path': None,
            'srt_path': None,
            'duration': None,
        })

        # Add duration to metadata
        if self.duration is not None:
            self.metadata['duration'] = self.duration

    @property
    def audio_file(self) -> Optional[Path]:
        """Get audio path as Path object."""
        return Path(self.audio_path) if self.audio_path else None

    @property
    def srt_file(self) -> Optional[Path]:
        """Get SRT path as Path object."""
        return Path(self.srt_path) if self.srt_path else None


__all__ = ["TTSResult"]
