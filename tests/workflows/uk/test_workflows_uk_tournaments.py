"""Tests for the Tennis-Data UK tournaments workflow (`workflows.uk.tournaments`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.datasources.tennis_data_uk.client import Tour
from tennis_data_pipeline.handler.uk.cleaner.tournaments import TournamentTable
from tennis_data_pipeline.workflows.uk import tournaments as tournaments_module
from tennis_data_pipeline.workflows.uk.clean import clean_checkpoint_path
from tennis_data_pipeline.workflows.uk.tournaments import (
    build_uk_tournaments,
    tournament_inconsistencies_path,
    tournament_table_path,
)


def test_tournament_table_path_uses_the_configured_filename_template(tmp_path: Path) -> None:
    uk_settings = settings.tennis_data_uk
    expected_name = uk_settings.tournament_filename_template.format(tour="atp")

    assert tournament_table_path(Tour.ATP, tmp_path) == (
        tmp_path / "atp" / uk_settings.tournament_dir_name / expected_name
    )


def test_tournament_inconsistencies_path_uses_the_configured_filename_template(tmp_path: Path) -> None:
    uk_settings = settings.tennis_data_uk
    expected_name = uk_settings.tournament_inconsistencies_filename_template.format(tour="atp")

    assert tournament_inconsistencies_path(Tour.ATP, tmp_path) == (
        tmp_path / "atp" / uk_settings.tournament_dir_name / expected_name
    )


def _write_dummy_clean_checkpoint(tour: Tour, year: int, clean_dir: Path) -> None:
    path = clean_checkpoint_path(tour, year, clean_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("dummy\n")


def test_build_uk_tournaments_skips_years_without_a_clean_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_dummy_clean_checkpoint(Tour.ATP, 2020, tmp_path)
    # 2021 deliberately has no clean checkpoint on disk.

    loaded_for = []
    monkeypatch.setattr(
        tournaments_module,
        "load_clean_uk_data",
        lambda path, tour: loaded_for.append(path) or pd.DataFrame({"x": [1]}),
    )
    monkeypatch.setattr(
        tournaments_module,
        "build_uk_tournament_table",
        lambda df: TournamentTable(
            tournaments=pd.DataFrame(
                {"tour": ["atp"], "year": [2020], "uk_tournament_id": [1], "location": ["X"]}
            ),
            inconsistencies=pd.DataFrame(),
        ),
    )

    table_path, num_tournaments, num_inconsistencies = build_uk_tournaments(
        Tour.ATP, [2020, 2021], clean_dir=tmp_path
    )

    assert loaded_for == [clean_checkpoint_path(Tour.ATP, 2020, tmp_path)]
    assert table_path == tournament_table_path(Tour.ATP, tmp_path)
    assert num_tournaments == 1
    assert num_inconsistencies == 0
    assert pd.read_csv(table_path).shape[0] == 1


def test_build_uk_tournaments_raises_when_no_year_has_a_clean_checkpoint(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        build_uk_tournaments(Tour.ATP, [2099], clean_dir=tmp_path)


def test_build_uk_tournaments_writes_inconsistencies_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_dummy_clean_checkpoint(Tour.ATP, 2020, tmp_path)
    monkeypatch.setattr(
        tournaments_module, "load_clean_uk_data", lambda path, tour: pd.DataFrame({"x": [1]})
    )
    monkeypatch.setattr(
        tournaments_module,
        "build_uk_tournament_table",
        lambda df: TournamentTable(
            tournaments=pd.DataFrame(
                {"tour": ["atp"], "year": [2020], "uk_tournament_id": [1], "location": ["X"]}
            ),
            inconsistencies=pd.DataFrame(
                {"tour": ["atp"], "year": [2020], "uk_tournament_id": [1], "location": ["X"]}
            ),
        ),
    )

    _, _, num_inconsistencies = build_uk_tournaments(Tour.ATP, [2020], clean_dir=tmp_path)

    assert num_inconsistencies == 1
    assert tournament_inconsistencies_path(Tour.ATP, tmp_path).exists()
