"""图像生成步骤结果类型

Result types for image generation steps.
"""
from dataclasses import dataclass, field
from typing import List

from .base import StepResult


@dataclass
class ImageResult(StepResult):
    """Result from image generation step.

    Contains:
    - image_paths: List of generated image paths
    - selected_images: List of selected image paths
    - generation_time: Total generation time
    - parallel_count: Number of parallel tasks used
    """

    _default_step_name: str = "ImageGeneration"

    image_paths: List[str] = field(default_factory=list)
    selected_images: List[str] = field(default_factory=list)
    generation_time: float = 0.0
    parallel_count: int = 0

    def __post_init__(self):
        """Validate and set data."""
        self._set_default_step_name()

        # Auto-populate data from fields
        self._auto_populate_data({
            'image_paths': None,
            'selected_images': None,
        })

        # Add metadata
        self.metadata['image_count'] = len(self.image_paths)
        self.metadata['generation_time'] = self.generation_time
        if self.parallel_count > 0:
            self.metadata['parallel_count'] = self.parallel_count

    @property
    def image_count(self) -> int:
        """Get number of images."""
        return len(self.image_paths)

    def get_image_path(self, index: int) -> str:
        """Get image path by index.

        Args:
            index: Image index

        Returns:
            Image path or None
        """
        if 0 <= index < len(self.image_paths):
            return self.image_paths[index]
        return None

    @property
    def speedup_factor(self) -> float:
        """Calculate theoretical speedup from parallelization.

        Returns:
            Speedup factor (parallel_count if generation_time > 0)
        """
        if self.parallel_count > 0 and self.generation_time > 0:
            return self.parallel_count
        return 1.0


__all__ = ["ImageResult"]
