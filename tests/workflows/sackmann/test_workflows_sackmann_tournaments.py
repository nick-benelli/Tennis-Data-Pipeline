"""Tests for the Sackmann tournaments workflow (`workflows.sackmann.tournaments`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.datasources.sackmann.client import Tour
from tennis_data_pipeline.handler.uk.cleaner.tournaments import TournamentTable
from tennis_data_pipeline.workflows.sackmann import tournaments as tournaments_module
from tennis_data_pipeline.workflows.sackmann.tournaments import (
    build_sackmann_tournaments,
    tournament_inconsistencies_path,
    tournament_table_path,
)


def test_tournament_table_path_uses_the_configured_filename_template(tmp_path: Path) -> None:
    sackmann_settings = settings.sackmann
    expected_name = sackmann_settings.tournament_filename_template.format(tour="atp")

    assert tournament_table_path(Tour.ATP, tmp_path) == (
        tmp_path / "atp" / sackmann_settings.tournament_dir_name / expected_name
    )


def test_tournament_inconsistencies_path_uses_the_configured_filename_template(tmp_path: Path) -> None:
    sackmann_settings = settings.sackmann
    expected_name = sackmann_settings.tournament_inconsistencies_filename_template.format(tour="atp")

    assert tournament_inconsistencies_path(Tour.ATP, tmp_path) == (
        tmp_path / "atp" / sackmann_settings.tournament_dir_name / expected_name
    )


def test_build_sackmann_tournaments_loads_via_the_tour_specific_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_calls = []
    monkeypatch.setattr(
        tournaments_module.atp,
        "load_years",
        lambda years: load_calls.append(list(years)) or pd.DataFrame({"tourney_id": ["2020-1"]}),
    )
    monkeypatch.setattr(
        tournaments_module,
        "build_sackmann_tournament_table",
        lambda df: TournamentTable(
            tournaments=pd.DataFrame({"tour": ["atp"], "year": [2020], "tourney_id": ["2020-1"]}),
            inconsistencies=pd.DataFrame(),
        ),
    )

    table_path, num_tournaments, num_inconsistencies = build_sackmann_tournaments(
        Tour.ATP, [2020], clean_dir=tmp_path
    )

    assert load_calls == [[2020]]
    assert table_path == tournament_table_path(Tour.ATP, tmp_path)
    assert num_tournaments == 1
    assert num_inconsistencies == 0
    assert pd.read_csv(table_path).shape[0] == 1


def test_build_sackmann_tournaments_raises_when_no_matches_are_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(tournaments_module.atp, "load_years", lambda years: pd.DataFrame())

    with pytest.raises(ValueError, match="No matches returned"):
        build_sackmann_tournaments(Tour.ATP, [2020])


def test_build_sackmann_tournaments_writes_inconsistencies_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        tournaments_module.wta, "load_years", lambda years: pd.DataFrame({"tourney_id": ["2020-1"]})
    )
    monkeypatch.setattr(
        tournaments_module,
        "build_sackmann_tournament_table",
        lambda df: TournamentTable(
            tournaments=pd.DataFrame({"tour": ["wta"], "year": [2020], "tourney_id": ["2020-1"]}),
            inconsistencies=pd.DataFrame({"tour": ["wta"], "year": [2020], "tourney_id": ["2020-1"]}),
        ),
    )

    _, _, num_inconsistencies = build_sackmann_tournaments(Tour.WTA, [2020], clean_dir=tmp_path)

    assert num_inconsistencies == 1
    assert tournament_inconsistencies_path(Tour.WTA, tmp_path).exists()
