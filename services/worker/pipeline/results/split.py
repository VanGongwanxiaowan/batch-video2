"""文本分镜步骤结果类型

Result types for text splitting steps.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .base import StepResult


@dataclass
class SplitResult(StepResult):
    """Result from text splitting step.

    Contains:
    - splits: List of split dictionaries
    - split_count: Number of splits
    """

    _default_step_name: str = "TextSplit"

    splits: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields
        self._auto_populate_data({
            'splits': None,
        })

        # Add split count to metadata
        self.metadata['split_count'] = len(self.splits)

    @property
    def split_count(self) -> int:
        """Get number of splits."""
        return len(self.splits)

    def get_split(self, index: int) -> Optional[Dict[str, Any]]:
        """Get a specific split by index.

        Args:
            index: Split index

        Returns:
            Split dictionary or None
        """
        if 0 <= index < len(self.splits):
            return self.splits[index]
        return None


__all__ = ["SplitResult"]
