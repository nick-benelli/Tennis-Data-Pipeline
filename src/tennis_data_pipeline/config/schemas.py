"""Pydantic models for the application config."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# src/tennis_data_pipeline/config/schemas.py -> repo root
_DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[3]


class PathsSettings(BaseSettings):
    """Filesystem locations, overridable via TENNIS_DATA_PIPELINE_* env vars."""

    model_config = SettingsConfigDict(env_prefix="TENNIS_DATA_PIPELINE_", extra="ignore")

    # Override with TENNIS_DATA_PIPELINE_PROJECT_DIR when data lives outside the repo checkout.
    project_dir: Path = Field(default=_DEFAULT_PROJECT_DIR)


class TennisDataUKSettings(BaseSettings):
    """Tennis-Data.co.uk client configuration, overridable via TENNIS_DATA_UK_* env vars."""

    model_config = SettingsConfigDict(env_prefix="TENNIS_DATA_UK_", extra="ignore")

    request_timeout_seconds: float = Field(default=15.0, gt=0)
    retry_total: int = Field(default=3, ge=0)
    retry_backoff_factor: float = Field(default=0.5, ge=0)
    # Not used by the client yet; reserved for a possible GitHub-mirror fallback source.
    github_user: str = "nick-benelli"
    github_repo: str = "Tennis-Data-Pipeline"

    # Tennis-Data.co.uk inserts a randomized path segment before each season's file
    # (e.g. "hrjk-85HytOjkhth76j_ygh4jf7" in ".../hrjk-.../2024/2024.xlsx"). It has
    # changed at least once already, so it's exposed here (and via env var) rather
    # than baked directly into the URL builder. If downloads start 404ing, call
    # TennisDataUKClient.discover_path_prefix() to scrape the current value from
    # https://www.tennis-data.co.uk/data.php, or set TENNIS_DATA_UK_PATH_PREFIX.
    path_prefix: str = "hrjk-85HytOjkhth76j_ygh4jf7"


class Settings(BaseModel):
    """Top-level application settings."""

    paths: PathsSettings = Field(default_factory=PathsSettings)
    tennis_data_uk: TennisDataUKSettings = Field(default_factory=TennisDataUKSettings)

