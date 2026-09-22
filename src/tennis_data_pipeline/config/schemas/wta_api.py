"""WTA tournaments API data source configuration schema."""

from __future__ import annotations
from typing import Any
from pydantic import field_validator
from .base import StrictModel, _is_unresolved_env_placeholder, _field_default, _normalize_bool


class WtaApiConfig(StrictModel):
    """api.wtatennis.com tournaments-endpoint settings."""

    base_url: str = "https://api.wtatennis.com"
    request_timeout_seconds: float = 30.0
    retry_total: int = 3
    retry_backoff_factor: float = 0.5
    page_size: int = 1000
    # The site's TLS certificate fails verification as of 2026-09; disable
    # verification rather than silently retry insecurely per-request.
    verify_ssl: bool = False

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
            raise ValueError("wta_api.request_timeout_seconds must be greater than zero")
        return timeout

    @field_validator("retry_total", mode="before")
    @classmethod
    def normalize_retry_total(cls, value: Any) -> int:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_total")
        retries = int(value)
        if retries < 0:
            raise ValueError("wta_api.retry_total must be greater than or equal to zero")
        return retries

    @field_validator("retry_backoff_factor", mode="before")
    @classmethod
    def normalize_retry_backoff_factor(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_backoff_factor")
        backoff = float(value)
        if backoff < 0:
            raise ValueError("wta_api.retry_backoff_factor must be greater than or equal to zero")
        return backoff

    @field_validator("page_size", mode="before")
    @classmethod
    def normalize_page_size(cls, value: Any) -> int:
        """Fall back to the default if unset/an unresolved env placeholder, else validate > 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "page_size")
        page_size = int(value)
        if page_size <= 0:
            raise ValueError("wta_api.page_size must be greater than zero")
        return page_size

    @field_validator("verify_ssl", mode="before")
    @classmethod
    def normalize_verify_ssl(cls, value: Any, info: Any) -> bool:
        """If the value is None or an unresolved env placeholder, return the default."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return _normalize_bool(value, _field_default(cls, info.field_name))
