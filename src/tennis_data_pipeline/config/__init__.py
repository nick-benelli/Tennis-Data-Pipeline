"""Application configuration."""

from __future__ import annotations

from .loader import load_settings
from .schemas import Settings, TennisDataUKSettings

settings = load_settings()

__all__ = ["Settings", "TennisDataUKSettings", "settings"]
