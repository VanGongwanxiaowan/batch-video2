"""字幕步骤结果类型

Result types for subtitle generation steps.
"""
from dataclasses import dataclass

from .base import StepResult


@dataclass
class SubtitleResult(StepResult):
    """Result from subtitle generation step.

    Contains:
    - srt_path: Path to generated subtitle file
    - subtitle_count: Number of subtitle entries
    """

    _default_step_name: str = "SubtitleGeneration"

    srt_path: Optional[str] = None
    subtitle_count: int = 0

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields
        self._auto_populate_data({
            'srt_path': None,
            'subtitle_count': None,
        })

        # Add subtitle count to metadata
        self.metadata['subtitle_count'] = self.subtitle_count


__all__ = ["SubtitleResult"]
