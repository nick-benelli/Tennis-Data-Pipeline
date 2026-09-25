"""Tests for `config.paths` (package/project directory constants)."""

from __future__ import annotations

from tennis_data_pipeline.config.paths import PACKAGE_DIR, PROJECT_DIR


def test_package_dir_points_at_the_tennis_data_pipeline_package() -> None:
    assert PACKAGE_DIR.name == "tennis_data_pipeline"
    assert (PACKAGE_DIR / "__init__.py").is_file()


def test_project_dir_is_the_repo_root_containing_pyproject_toml() -> None:
    assert (PROJECT_DIR / "pyproject.toml").is_file()


def test_project_dir_is_two_levels_above_the_package_dir() -> None:
    # src/tennis_data_pipeline -> src -> <project root>
    assert PROJECT_DIR == PACKAGE_DIR.parent.parent
