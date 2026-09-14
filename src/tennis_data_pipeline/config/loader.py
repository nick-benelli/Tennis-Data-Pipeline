"""Build the application settings."""

from __future__ import annotations

from .schemas import Settings


def load_settings() -> Settings:
    """Construct Settings, applying any environment variable overrides."""
    return Settings()
