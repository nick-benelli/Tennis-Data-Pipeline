"""Tennis-Data.co.uk data source configuration schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from .base import StrictModel, _field_default, _is_unresolved_env_placeholder


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
    raw_filename_template: str = "uk_{tour}_singles_raw_{year}.csv"

    # Stage-4 clean checkpoint naming: written to
    # <paths.clean>/<clean_dir_name>/<tour>/<clean_filename_template>.
    clean_dir_name: str = "uk"
    clean_filename_template: str = "uk_{tour}_singles_clean_{year}.csv"
    # Shared ATP+WTA quality report, relative to <paths.clean>/<clean_dir_name>/.
    quality_report_relpath: str = "analysis/uk_quality_report.csv"

    # Tournament-summary table: written to
    # <paths.clean>/<clean_dir_name>/<tour>/<tournament_dir_name>/<tournament_filename_template>.
    tournament_dir_name: str = "tournaments"
    tournament_filename_template: str = "uk_{tour}_tournaments.csv"
    tournament_inconsistencies_filename_template: str = "uk_{tour}_tournament_inconsistencies.csv"

    @field_validator("request_timeout_seconds", mode="before")
    @classmethod
    def normalize_request_timeout(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate > 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "request_timeout_seconds")
        timeout = float(value)
        if timeout <= 0:
            raise ValueError("tennis_data_uk.request_timeout_seconds must be greater than zero")
        return timeout

    @field_validator("retry_total", mode="before")
    @classmethod
    def normalize_retry_total(cls, value: Any) -> int:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_total")
        retries = int(value)
        if retries < 0:
            raise ValueError("tennis_data_uk.retry_total must be greater than or equal to zero")
        return retries

    @field_validator("retry_backoff_factor", mode="before")
    @classmethod
    def normalize_retry_backoff_factor(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate >= 0."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "retry_backoff_factor")
        backoff = float(value)
        if backoff < 0:
            raise ValueError("tennis_data_uk.retry_backoff_factor must be greater than or equal to zero")
        return backoff

    @field_validator(
        "path_prefix",
        "github_user",
        "github_repo",
        "raw_dir_name",
        "raw_filename_template",
        "clean_dir_name",
        "clean_filename_template",
        "quality_report_relpath",
        mode="before",
    )
    @classmethod
    def normalize_string_defaults(cls, value: Any, info: Any) -> str:
        """Fall back to the field's default if unset or an unresolved env placeholder."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, info.field_name)
        return str(value)
