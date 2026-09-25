"""Tests for `config.loader` (env-var substitution, config resolution/loading, settings cache)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tennis_data_pipeline.config import loader
from tennis_data_pipeline.config.loader import (
    _SettingsProxy,
    _substitute_env_vars,
    clear_config_cache,
    get_config_dict,
    get_settings,
    load_app_config,
    load_raw_config,
    reload_config,
    resolve_config_path,
)
from tennis_data_pipeline.config.schemas import AppConfig


@pytest.fixture(autouse=True)
def _clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test controls config resolution explicitly - never inherit a real .env."""
    monkeypatch.delenv("TENNIS_DATA_PIPELINE_CONFIG", raising=False)


# --- _substitute_env_vars ----------------------------------------------------


def test_substitute_env_vars_replaces_set_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_VAR", "hello")
    assert _substitute_env_vars("value: ${MY_VAR}") == "value: hello"


def test_substitute_env_vars_uses_default_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MY_VAR", raising=False)
    assert _substitute_env_vars("value: ${MY_VAR:fallback}") == "value: fallback"


def test_substitute_env_vars_env_value_wins_even_if_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_VAR", "")
    assert _substitute_env_vars("value: ${MY_VAR:fallback}") == "value: "


def test_substitute_env_vars_leaves_placeholder_when_unset_and_no_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MY_VAR", raising=False)
    assert _substitute_env_vars("value: ${MY_VAR}") == "value: ${MY_VAR}"


# --- resolve_config_path ------------------------------------------------------


def test_resolve_config_path_resolves_an_explicit_relative_path(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api: {}\n")

    assert resolve_config_path(config_file) == config_file.resolve()


def test_resolve_config_path_falls_back_to_env_var(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api: {}\n")
    monkeypatch.setenv("TENNIS_DATA_PIPELINE_CONFIG", str(config_file))

    assert resolve_config_path() == config_file.resolve()


def test_resolve_config_path_raises_when_env_var_path_does_not_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TENNIS_DATA_PIPELINE_CONFIG", str(tmp_path / "missing.yaml"))

    with pytest.raises(FileNotFoundError):
        resolve_config_path()


def test_resolve_config_path_raises_when_nothing_can_be_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Neutralize every fallback (a real local .env/pyproject.toml/user config must not leak in).
    monkeypatch.setattr(loader, "find_dotenv", lambda *_a, **_k: "")
    monkeypatch.setattr(loader, "load_dotenv", lambda *_a, **_k: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    with pytest.raises(FileNotFoundError, match="No config file found"):
        resolve_config_path()


# --- load_raw_config / load_app_config ---------------------------------------


def test_load_raw_config_substitutes_env_vars_from_yaml_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TIMEOUT", "45")
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api:\n  timeout_seconds: ${MY_TIMEOUT:30}\n")

    raw = load_raw_config(config_file)

    assert raw == {"api": {"timeout_seconds": 45}}


def test_load_raw_config_returns_empty_dict_for_empty_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    assert load_raw_config(config_file) == {}


def test_load_app_config_validates_defaults_from_an_empty_file(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    app_config = load_app_config(config_file)

    assert isinstance(app_config, AppConfig)
    assert app_config.api.timeout_seconds == AppConfig().api.timeout_seconds


def test_load_app_config_applies_values_from_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api:\n  timeout_seconds: 12.5\n")

    app_config = load_app_config(config_file)

    assert app_config.api.timeout_seconds == 12.5


# --- get_settings caching -----------------------------------------------------


def test_get_settings_caches_by_resolved_config_path(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    assert get_settings(config_file) is get_settings(config_file)


def test_clear_config_cache_forces_a_fresh_load(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    first = get_settings(config_file)
    clear_config_cache()
    second = get_settings(config_file)

    assert first is not second


def test_reload_config_reflects_changes_made_to_the_file_on_disk(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api:\n  timeout_seconds: 10\n")
    get_settings(config_file)

    config_file.write_text("api:\n  timeout_seconds: 20\n")
    reloaded = reload_config(config_file)

    assert reloaded.api.timeout_seconds == 20


def test_get_config_dict_matches_get_settings_dump(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    assert get_config_dict(config_file) == get_settings(config_file).model_dump(exclude_none=True)


# --- _SettingsProxy ------------------------------------------------------------


def test_settings_proxy_lazily_delegates_to_get_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("api:\n  timeout_seconds: 99\n")
    monkeypatch.setenv("TENNIS_DATA_PIPELINE_CONFIG", str(config_file))

    proxy = _SettingsProxy()

    assert proxy.api.timeout_seconds == 99
