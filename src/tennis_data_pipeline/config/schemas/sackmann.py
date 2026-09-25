"""Sackmann tennis archive mirror configuration schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from .base import StrictModel, _field_default, _is_unresolved_env_placeholder


class SackmannConfig(StrictModel):
    """Sackmann tennis archive mirror (Aneeshers/tennis-sackmann-archive) settings."""

    base_url: str = "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main"
    request_timeout_seconds: float = 30.0
    retry_total: int = 3
    retry_backoff_factor: float = 1.0

    # Tournament-summary table: written to
    # <paths.clean>/<clean_dir_name>/<tour>/<tournament_dir_name>/<tournament_filename_template>.
    clean_dir_name: str = "sackmann"
    tournament_dir_name: str = "tournaments"
    tournament_filename_template: str = "sackmann_{tour}_tournaments.csv"
    tournament_inconsistencies_filename_template: str = "sackmann_{tour}_tournament_inconsistencies.csv"

    @field_validator("base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: Any) -> str:
        """Fall back to the default if unset or an unresolved env placeholder."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "base_url")
        return str(value)

    @field_validator("request_timeout_seconds", mode="before")
    @classmethod
    def normalize_request_timeout(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate > 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "request_timeout_seconds")
        timeout = float(value)
        if timeout <= 0:
            raise ValueError("sackmann.request_timeout_seconds must be greater than zero")
        return timeout

    @field_validator("retry_total", mode="before")
    @classmethod
    def normalize_retry_total(cls, value: Any) -> int:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_total")
        retries = int(value)
        if retries < 0:
            raise ValueError("sackmann.retry_total must be greater than or equal to zero")
        return retries

    @field_validator("retry_backoff_factor", mode="before")
    @classmethod
    def normalize_retry_backoff_factor(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_backoff_factor")
        backoff = float(value)
        if backoff < 0:
            raise ValueError("sackmann.retry_backoff_factor must be greater than or equal to zero")
        return backoff
