"""Pipeline 步骤结果基类定义

Base result types and error handling for pipeline steps.
"""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Generic

from core.logging_config import setup_logging

logger = setup_logging(__name__)


T = TypeVar('T')


@dataclass
class StepResult:
    """Base class for step execution results.

    Each step returns a StepResult (or subclass) containing:
    - step_name: Name of the step that produced this result
    - data: The actual output data
    - metadata: Additional metadata (execution time, status, etc.)

    This design allows steps to be pure functions that don't mutate context.
    """

    step_name: str
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Default step name for subclasses (override in subclass)
    _default_step_name: str = "Step"

    def __post_init__(self):
        """Validate and log result creation."""
        if not self.step_name:
            raise ValueError("step_name cannot be empty")

        logger.debug(
            f"Created StepResult: step_name={self.step_name}, "
            f"data_keys={list(self.data.keys())}, "
            f"metadata_keys={list(self.metadata.keys())}"
        )

    def _auto_populate_data(
        self,
        field_mappings: Dict[str, Optional[str]]
    ) -> None:
        """Auto-populate data dict from instance fields.

        Helper method for subclasses to eliminate duplication in __post_init__.

        Args:
            field_mappings: Dict mapping {field_name: data_key}
                          If data_key is None, uses field_name as key
                          Only includes non-None/non-empty values

        Example:
            self._auto_populate_data({
                'audio_path': None,      # data['audio_path'] = self.audio_path
                'duration': 'audio_duration',  # data['audio_duration'] = self.duration
            })
        """
        for field_name, data_key in field_mappings.items():
            # Guard clause: skip if field doesn't exist
            if not hasattr(self, field_name):
                continue

            value = getattr(self, field_name)

            # Guard clause: skip None values
            if value is None:
                continue

            # Guard clause: skip empty collections
            if isinstance(value, (list, dict)) and len(value) == 0:
                continue

            # Use field_name as data_key if not specified
            key = data_key if data_key is not None else field_name
            self.data[key] = value

    def _set_default_step_name(self) -> None:
        """Set default step name if not provided.

        Helper for subclasses to use in their __post_init__.
        """
        if not hasattr(self, 'step_name') or not self.step_name:
            self.step_name = self._default_step_name

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from data dict.

        Args:
            key: Key to retrieve
            default: Default value if key not found

        Returns:
            The value or default
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if key exists in data.

        Args:
            key: Key to check

        Returns:
            True if key exists
        """
        return key in self.data

    def set(self, key: str, value: Any) -> None:
        """Set a value in data dict.

        Args:
            key: Key to set
            value: Value to set
        """
        self.data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "step": self.step_name,
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_context(
        cls,
        step_name: str,
        context: 'PipelineContext',
        keys: List[str]
    ) -> 'StepResult':
        """Create StepResult from context attributes.

        This is a compatibility helper for migrating from context-based steps.

        Args:
            step_name: Name of the step
            context: PipelineContext instance
            keys: List of attribute names to copy from context

        Returns:
            StepResult with data copied from context
        """
        data = {}
        for key in keys:
            if hasattr(context, key):
                value = getattr(context, key)
                # Only include non-None values
                if value is not None:
                    data[key] = value

        return cls(step_name=step_name, data=data)

    def merge_to_context(self, context: 'PipelineContext') -> None:
        """Merge result data into PipelineContext.

        This is a compatibility helper for gradual migration.

        Args:
            context: PipelineContext to merge into
        """
        for key, value in self.data.items():
            setattr(context, key, value)


@dataclass
class StepError:
    """Represents an error that occurred during step execution.

    Attributes:
        step_name: Name of the step that failed
        error_type: Type of error
        error_message: Error message
        traceback: Optional traceback string
        timestamp: When the error occurred
        context: Optional context data
    """

    step_name: str
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_name": self.step_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }

    def __str__(self) -> str:
        """String representation."""
        return f"{self.step_name}: {self.error_type} - {self.error_message}"


# Type aliases for better readability
StepResultType = TypeVar('StepResultType', bound=StepResult)


__all__ = [
    "StepResult",
    "StepError",
    "StepResultType",
]
