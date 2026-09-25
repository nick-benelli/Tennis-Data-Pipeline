"""Logging configuration schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from .base import StrictModel, _field_default, _is_unresolved_env_placeholder


class LoggingConfig(StrictModel):
    """Logging configuration."""

    output: str = "console"  # Options: console, file, both
    file_path: str = "logs/tennis_data_pipeline.log"
    level: str = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @field_validator("output", mode="before")
    @classmethod
    def normalize_output(cls, value: Any) -> str:
        """Normalize logging output option."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "output")
        output = str(value).lower()
        if output not in {"console", "file", "both"}:
            raise ValueError(f"logging.output must be 'console', 'file', or 'both', got: {output}")
        return output

    @field_validator("file_path", mode="before")
    @classmethod
    def normalize_file_path(cls, value: Any) -> str:
        """Normalize log file path."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "file_path")
        return str(value)

    @field_validator("level", mode="before")
    @classmethod
    def normalize_level(cls, value: Any) -> str:
        """Normalize logging level."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "level")
        level = str(value).upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if level not in valid_levels:
            raise ValueError(f"logging.level must be one of {valid_levels}, got: {level}")
        return level

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(cls, value: Any) -> str:
        """Normalize log format string."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "format")
        return str(value)
