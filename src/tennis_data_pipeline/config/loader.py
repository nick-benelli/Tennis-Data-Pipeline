"""Configuration loading and validation for the tennis data pipeline.

Provides a clean separation between path resolution, raw config loading,
validation, and caching. Uses pathlib for modern path handling.
"""

from __future__ import annotations

import os
import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import find_dotenv, load_dotenv

from .schemas import AppConfig

# Matches ${VAR} or ${VAR:default}. Unlike `string.Template`, this supports a
# shell-style `:default` fallback so config.yaml can document per-key defaults
# directly, instead of only relying on the pydantic model's own defaults.
_ENV_VAR_PATTERN = re.compile(
    r"\$\{(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?::(?P<default>[^}]*))?\}"
)


def _get_default_config_path() -> Path:
    """Find config path with production-ready fallback strategy.

    Resolution order:
    1. TENNIS_DATA_PIPELINE_CONFIG environment variable
    2. configs/config.yaml relative to project root (pyproject.toml location)
    3. ~/.config/tennis-data-pipeline/config.yaml (user config directory)

    Returns:
        Resolved config path

    Raises:
        FileNotFoundError: If no config file found in any location
    """
    # Load .env file first so TENNIS_DATA_PIPELINE_CONFIG is available
    load_dotenv()

    # 1. Check environment variable (highest priority)
    env_config = os.getenv("TENNIS_DATA_PIPELINE_CONFIG")
    if env_config:
        path = Path(env_config).expanduser().resolve()
        if path.exists():
            return path
        raise FileNotFoundError(
            f"Config path from TENNIS_DATA_PIPELINE_CONFIG not found: {path}"
        )

    # 2. Check project-relative path (works for repo checkouts, GitHub Actions)
    pyproject_path = find_dotenv("pyproject.toml")
    if pyproject_path:
        project_config = Path(pyproject_path).parent / "configs" / "config.yaml"
        if project_config.exists():
            return project_config

    # 3. Check user config directory (XDG-style for installed packages)
    user_config = Path.home() / ".config" / "tennis-data-pipeline" / "config.yaml"
    if user_config.exists():
        return user_config

    # 4. Nothing found - provide helpful error
    project_str = (
        str(project_config)
        if pyproject_path
        else "configs/config.yaml (no pyproject.toml found)"
    )
    raise FileNotFoundError(
        f"No config file found. Tried:\n"
        f"  - TENNIS_DATA_PIPELINE_CONFIG env var\n"
        f"  - {project_str}\n"
        f"  - {user_config}\n"
        f"Set TENNIS_DATA_PIPELINE_CONFIG=/path/to/config.yaml or place config "
        f"in one of the above locations."
    )


def resolve_config_path(path: str | Path | None = None) -> Path:
    """Resolve config path to absolute Path.

    Args:
        path: Optional explicit config path. If None, uses default resolution.

    Returns:
        Resolved absolute Path to config file
    """
    if path is not None:
        return Path(path).expanduser().resolve()
    return _get_default_config_path()


def _substitute_env_vars(content: str) -> str:
    """Substitute ${VAR} / ${VAR:default} placeholders with environment values.

    If VAR is set in the environment, its value is used (even if empty). If
    unset and a `:default` is present, the default is used. If unset with no
    default, the placeholder is left as-is so the pydantic model's own field
    default can take over (see `_is_unresolved_env_placeholder` in schemas.py).
    """

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        default = match.group("default")
        if name in os.environ:
            return os.environ[name]
        return default if default is not None else match.group(0)

    return _ENV_VAR_PATTERN.sub(_replace, content)


def load_raw_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load YAML config with ${VAR}/${VAR:default} substitution from environment."""
    load_dotenv()

    config_path = resolve_config_path(path)
    content = config_path.read_text(encoding="utf-8")
    substituted = _substitute_env_vars(content)
    return yaml.safe_load(substituted) or {}


def load_app_config(path: str | Path | None = None) -> AppConfig:
    """Load and validate config from disk (uncached)."""
    raw_config = load_raw_config(path)
    return AppConfig.model_validate(raw_config)


def get_settings(path: str | Path | None = None) -> AppConfig:
    """Return cached validated application settings."""
    resolved = resolve_config_path(path)
    return _cached_load(resolved)


def get_config_dict(path: str | Path | None = None) -> dict[str, Any]:
    """Get cached config as a dictionary."""
    return get_settings(path).model_dump(exclude_none=True)


def get_project_root() -> Path:
    """
    Find the project root directory.

    Returns:
        Path to project root (where pyproject.toml lives)

    Raises:
        FileNotFoundError: If pyproject.toml cannot be found
    """
    pyproject_path = find_dotenv("pyproject.toml")
    if not pyproject_path:
        raise FileNotFoundError(
            "Could not find pyproject.toml. Unable to determine project root."
        )
    return Path(pyproject_path).parent


def clear_config_cache() -> None:
    """Clear the cache, forcing next get_settings() to reload from disk."""
    _cached_load.cache_clear()


def reload_config(path: str | Path | None = None) -> AppConfig:
    """Clear cache and reload config from disk."""
    clear_config_cache()
    return get_settings(path)


@cache
def _cached_load(resolved_path: Path) -> AppConfig:
    """Internal cached loader."""
    return load_app_config(resolved_path)


class _SettingsProxy:
    """Lazily loads and caches `AppConfig` on first attribute access.

    Lets call sites do `from tennis_data_pipeline.config import settings` and
    then `settings.api.timeout_seconds`, etc., without loading/parsing the
    config file at import time.
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_settings(), name)


settings = _SettingsProxy()


__all__ = [
    "clear_config_cache",
    "get_config_dict",
    "get_project_root",
    "get_settings",
    "load_app_config",
    "load_raw_config",
    "reload_config",
    "resolve_config_path",
    "settings",
]
