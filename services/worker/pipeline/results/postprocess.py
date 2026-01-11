"""后期处理步骤结果类型

Result types for post-processing steps.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .base import StepResult


@dataclass
class PostProcessResult(StepResult):
    """Result from post-processing step.

    Contains:
    - final_video_path: Path to final processed video
    - processing_steps: List of processing steps applied
    """

    _default_step_name: str = "PostProcessing"

    final_video_path: Optional[str] = None
    processing_steps: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields (final_video_path may be None)
        self.data = {}
        if self.final_video_path is not None:
            self.data['final_video_path'] = self.final_video_path
        self.data['processing_steps'] = self.processing_steps

        # Add metadata
        self.metadata['processing_steps'] = self.processing_steps

    @property
    def final_video_file(self) -> Optional[Path]:
        """Get final video path as Path object."""
        return Path(self.final_video_path) if self.final_video_path else None


__all__ = ["PostProcessResult"]
