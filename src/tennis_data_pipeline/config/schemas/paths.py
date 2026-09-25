"""Paths configuration schema."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from ..paths import PROJECT_DIR
from .base import StrictModel, _field_default, _is_unresolved_env_placeholder


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
    mapping_dir: str = "data/mapping"
    linked_dir: str = "data/linked"

    @field_validator("project_dir", mode="before")
    @classmethod
    def normalize_project_dir(cls, value: Any) -> Any:
        """If the value is None or an unresolved env placeholder, fall back to the
        auto-detected project root (the repo containing pyproject.toml).
        """
        if value is None or _is_unresolved_env_placeholder(value):
            return PROJECT_DIR
        return Path(value).expanduser().resolve()

    @field_validator(
        "data_dir", "raw_dir", "clean_dir", "archive_dir", "mapping_dir", "linked_dir", mode="before"
    )
    @classmethod
    def normalize_dir_defaults(cls, value: Any, info: Any) -> str:
        """If the value is None or an unresolved env placeholder, return the default.
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

    @property
    def mapping(self) -> Path:
        """Absolute path to the cross-source id-mapping data directory."""
        return self._resolve(self.mapping_dir)

    @property
    def linked(self) -> Path:
        """Absolute path to the formalized per-year match-linkage output directory."""
        return self._resolve(self.linked_dir)
