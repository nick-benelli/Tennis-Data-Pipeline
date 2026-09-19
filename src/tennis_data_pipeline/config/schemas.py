"""Pydantic models for the application config."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .paths import PROJECT_DIR

_ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{[^}]+\}$")


def _is_unresolved_env_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(_ENV_PLACEHOLDER_PATTERN.fullmatch(value))


def _field_default(model_cls: type[BaseModel], field_name: str) -> Any:
    """Return a model field default in a type-checker-friendly way."""

    return model_cls.__pydantic_fields__[field_name].default


def _normalize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value) if value is not None else default


class StrictModel(BaseModel):
    """Base model that rejects unknown config keys."""

    model_config = ConfigDict(extra="forbid")


class ApiConfig(StrictModel):
    """Default HTTP client behavior shared by data sources."""

    verify_ssl: bool = True
    timeout_seconds: float = 30.0
    retry_insecure_on_ssl_error: bool = True
    max_retries: int = 3
    backoff_seconds: float = 0.8

    @field_validator("verify_ssl", "retry_insecure_on_ssl_error", mode="before")
    @classmethod
    def normalize_bool_defaults(cls, value: Any, info: Any) -> bool:
        """
        If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return _normalize_bool(value, _field_default(cls, info.field_name))

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def normalize_timeout(cls, value: Any) -> float:
        """
        If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "timeout_seconds")
        timeout = float(value)
        if timeout <= 0:
            raise ValueError("api.timeout_seconds must be greater than zero")
        return timeout

    @field_validator("max_retries", mode="before")
    @classmethod
    def normalize_max_retries(cls, value: Any) -> int:
        """
        If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "max_retries")
        retries = int(value)
        if retries < 0:
            raise ValueError("api.max_retries must be greater than or equal to zero")
        return retries

    @field_validator("backoff_seconds", mode="before")
    @classmethod
    def normalize_backoff_seconds(cls, value: Any) -> float:
        """
        If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "backoff_seconds")
        backoff = float(value)
        if backoff < 0:
            raise ValueError(
                "api.backoff_seconds must be greater than or equal to zero"
            )
        return backoff


class PathsConfig(StrictModel):
    """Project directory layout.

    `data_dir`/`raw_dir`/`clean_dir`/`archive_dir` are resolved relative to
    `project_dir` unless given as absolute paths.
    """

    project_dir: Path = Field(default_factory=lambda: PROJECT_DIR)
    data_dir: str = "data"
    raw_dir: str = "data/raw"
    clean_dir: str = "data/clean"
    archive_dir: str = "data/archive"

    @field_validator("project_dir", mode="before")
    @classmethod
    def normalize_project_dir(cls, value: Any) -> Any:
        """
        If the value is None or an unresolved env placeholder, fall back to the
        auto-detected project root (the repo containing pyproject.toml).
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return PROJECT_DIR
        return Path(value).expanduser().resolve()

    @field_validator("data_dir", "raw_dir", "clean_dir", "archive_dir", mode="before")
    @classmethod
    def normalize_dir_defaults(cls, value: Any, info: Any) -> str:
        """
        If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return str(value)

    def _resolve(self, relative: str) -> Path:
        path = Path(relative)
        return path if path.is_absolute() else self.project_dir / path

    @property
    def data(self) -> Path:
        """Absolute path to the data root directory."""
        return self._resolve(self.data_dir)

    @property
    def raw(self) -> Path:
        """Absolute path to the raw (untouched, source-format) data directory."""
        return self._resolve(self.raw_dir)

    @property
    def clean(self) -> Path:
        """Absolute path to the cleaned/normalized data directory."""
        return self._resolve(self.clean_dir)

    @property
    def archive(self) -> Path:
        """Absolute path to the archived one-off snapshot data directory."""
        return self._resolve(self.archive_dir)


class TennisDataUKConfig(StrictModel):
    """Tennis-Data.co.uk data source settings."""

    request_timeout_seconds: float = 30.0
    retry_total: int = 3
    retry_backoff_factor: float = 0.5
    # Randomized path segment tennis-data.co.uk inserts before each season file.
    # Empty means "use the client's last-known default"; update this (or call
    # `TennisDataUKClient.discover_path_prefix()`) if downloads start 404ing.
    path_prefix: str = ""
    # GitHub mirror of scraped results (fallback data source); currently unused.
    github_user: str = ""
    github_repo: str = ""

    # Stage-2 raw checkpoint naming: written to
    # <paths.raw>/<raw_dir_name>/<tour>/<raw_filename_template>.
    raw_dir_name: str = "uk"
    raw_filename_template: str = "{tour}_singles_results_{year}.csv"

    @field_validator("request_timeout_seconds", mode="before")
    @classmethod
    def normalize_request_timeout(cls, value: Any) -> float:
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "request_timeout_seconds")
        timeout = float(value)
        if timeout <= 0:
            raise ValueError(
                "tennis_data_uk.request_timeout_seconds must be greater than zero"
            )
        return timeout

    @field_validator("retry_total", mode="before")
    @classmethod
    def normalize_retry_total(cls, value: Any) -> int:
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_total")
        retries = int(value)
        if retries < 0:
            raise ValueError(
                "tennis_data_uk.retry_total must be greater than or equal to zero"
            )
        return retries

    @field_validator("retry_backoff_factor", mode="before")
    @classmethod
    def normalize_retry_backoff_factor(cls, value: Any) -> float:
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_backoff_factor")
        backoff = float(value)
        if backoff < 0:
            raise ValueError(
                "tennis_data_uk.retry_backoff_factor must be greater than or equal to zero"
            )
        return backoff

    @field_validator(
        "path_prefix", "github_user", "github_repo",
        "raw_dir_name", "raw_filename_template",
        mode="before",
    )
    @classmethod
    def normalize_string_defaults(cls, value: Any, info: Any) -> str:
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return str(value)


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
            raise ValueError(
                f"logging.output must be 'console', 'file', or 'both', got: {output}"
            )
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
            raise ValueError(
                f"logging.level must be one of {valid_levels}, got: {level}"
            )
        return level

    @field_validator("format", mode="before")
    @classmethod
    def normalize_format(cls, value: Any) -> str:
        """Normalize log format string."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "format")
        return str(value)


class AppConfig(StrictModel):
    """Validated config root model."""

    api: ApiConfig = Field(default_factory=ApiConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    tennis_data_uk: TennisDataUKConfig = Field(default_factory=TennisDataUKConfig)
