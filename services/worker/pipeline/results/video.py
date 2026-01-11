"""视频合成步骤结果类型

Result types for video composition and digital human steps.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import StepResult


@dataclass
class VideoResult(StepResult):
    """Result from video composition step.

    Contains:
    - video_path: Path to composed video file
    - duration: Video duration in seconds
    - segment_count: Number of video segments
    """

    _default_step_name: str = "VideoComposition"

    video_path: Optional[str] = None
    duration: float = 0.0
    segment_count: int = 0

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields (video_path may be None)
        self.data = {}
        if self.video_path is not None:
            self.data['video_path'] = self.video_path
        self.data['duration'] = self.duration
        self.data['segment_count'] = self.segment_count

        # Add metadata
        self.metadata['duration'] = self.duration
        self.metadata['segment_count'] = self.segment_count

    @property
    def video_file(self) -> Optional[Path]:
        """Get video path as Path object."""
        return Path(self.video_path) if self.video_path else None


@dataclass
class DigitalHumanResult(StepResult):
    """Result from digital human step.

    Contains:
    - human_video_path: Path to digital human video
    - human_duration: Duration of digital human video
    """

    _default_step_name: str = "DigitalHuman"

    human_video_path: Optional[str] = None
    human_duration: float = 0.0

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields (human_video_path may be None)
        self.data = {}
        if self.human_video_path is not None:
            self.data['human_video_path'] = self.human_video_path
        self.data['human_duration'] = self.human_duration

        # Add metadata
        self.metadata['human_duration'] = self.human_duration

    @property
    def human_video_file(self) -> Optional[Path]:
        """Get human video path as Path object."""
        return Path(self.human_video_path) if self.human_video_path else None


__all__ = [
    "VideoResult",
    "DigitalHumanResult",
]
