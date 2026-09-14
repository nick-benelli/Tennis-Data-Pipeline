"""Pydantic models for the application config."""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TennisDataUKSettings(BaseSettings):
    """Tennis-Data.co.uk client configuration, overridable via TENNIS_DATA_UK_* env vars."""

    model_config = SettingsConfigDict(env_prefix="TENNIS_DATA_UK_", extra="ignore")

    request_timeout_seconds: float = Field(default=15.0, gt=0)
    retry_total: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, ge=0)
    # Not used by the client yet; reserved for a possible GitHub-mirror fallback source.
    github_user: str = "nick-benelli"
    github_repo: str = "Tennis-Data-Pipeline"


class Settings(BaseModel):
    """Top-level application settings."""

    tennis_data_uk: TennisDataUKSettings = Field(default_factory=TennisDataUKSettings)

