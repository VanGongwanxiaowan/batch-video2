"""Flux server configuration via environment variables."""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from core.config import BaseConfig, get_path_manager


class FluxConfig(BaseConfig):
    """Configuration schema for the Flux image server."""

    FLUX_MODEL_PATH: Optional[str] = None
    FLUX_LORA_BASE_PATH: Optional[str] = None
    FLUX_LORA_NAME: Optional[str] = None
    FLUX_LORA_STEP: int = 120
    FLUX_DEVICE_ID: str = "0"

    def _resolve_path(self, value: Optional[str], fallback: Path) -> Path:
        return Path(value).expanduser().resolve() if value else fallback

    @property
    def path_manager(self):
        return get_path_manager(self.BATCHSHORT_BASE_DIR)

    @property
    def model_path(self) -> Path:
        default = self.path_manager.worker_dir / "models" / "flux-1-dev"
        return self._resolve_path(self.FLUX_MODEL_PATH, default)

    @property
    def lora_base_path(self) -> Path:
        default = self.path_manager.shared_dir / "loras" / "flux"
        return self._resolve_path(self.FLUX_LORA_BASE_PATH, default)


@lru_cache()
def get_flux_config() -> FluxConfig:
    return FluxConfig()


