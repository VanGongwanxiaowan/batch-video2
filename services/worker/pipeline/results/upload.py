"""上传步骤结果类型

Result types for file upload steps.
"""
from dataclasses import dataclass, field
from typing import Dict

from .base import StepResult


@dataclass
class UploadResult(StepResult):
    """Result from upload step.

    Contains:
    - upload_urls: Dictionary of upload URLs
    - upload_status: Upload status
    - file_sizes: Dictionary of file sizes
    """

    _default_step_name: str = "Upload"

    upload_urls: Dict[str, str] = field(default_factory=dict)
    upload_status: str = "pending"
    file_sizes: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields (empty dicts are skipped by helper)
        self.data = {}
        if self.upload_urls:
            self.data['upload_urls'] = self.upload_urls
        self.data['upload_status'] = self.upload_status
        if self.file_sizes:
            self.data['file_sizes'] = self.file_sizes

        # Add metadata
        self.metadata['upload_status'] = self.upload_status
        if self.file_sizes:
            self.metadata['total_size'] = sum(self.file_sizes.values())

    @property
    def is_success(self) -> bool:
        """Check if upload was successful."""
        return self.upload_status == "success"

    @property
    def total_size(self) -> int:
        """Get total upload size."""
        return sum(self.file_sizes.values())


__all__ = ["UploadResult"]
