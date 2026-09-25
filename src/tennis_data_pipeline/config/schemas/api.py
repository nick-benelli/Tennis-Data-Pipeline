"""API client configuration schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from .base import StrictModel, _field_default, _is_unresolved_env_placeholder, _normalize_bool


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
        """If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return _normalize_bool(value, _field_default(cls, info.field_name))

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def normalize_timeout(cls, value: Any) -> float:
        """If the value is None or an unresolved env placeholder, return the default.
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
        """If the value is None or an unresolved env placeholder, return the default.
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
        """If the value is None or an unresolved env placeholder, return the default.
        This allows users to set env vars to empty or leave them unset to use defaults.
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "backoff_seconds")
        backoff = float(value)
        if backoff < 0:
            raise ValueError("api.backoff_seconds must be greater than or equal to zero")
        return backoff
