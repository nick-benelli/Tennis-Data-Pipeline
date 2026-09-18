"""Application configuration."""

from __future__ import annotations

from .loader import load_settings
from .schemas import PathsSettings, Settings, TennisDataUKSettings

settings = load_settings()

__all__ = ["PathsSettings", "Settings", "TennisDataUKSettings", "settings"]
