"""Tests for the Sackmann matches workflow (`workflows.sackmann.matches`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.datasources.sackmann.client import Tour
from tennis_data_pipeline.workflows.sackmann import matches as matches_module
from tennis_data_pipeline.workflows.sackmann.matches import load_local_matches, load_matches


def _raw_matches() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "score": ["6-2 6-3"],
            "best_of": pd.array([3], dtype="Int64"),
            "tourney_level": ["A"],
            "tourney_date": pd.to_datetime(["2021-01-01"]),
        }
    )


def test_load_matches_downloads_via_the_tour_specific_module_and_adds_score_features(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    load_calls = []
    monkeypatch.setattr(
        matches_module.atp,
        "load_years",
        lambda years, *, chronological=False: (
            load_calls.append((list(years), chronological)) or _raw_matches()
        ),
    )

    result = load_matches(Tour.ATP, [2021])

    assert load_calls == [([2021], False)]
    assert result.loc[0, "match_status"] == "completed"
    assert (result.loc[0, "set1_winner"], result.loc[0, "set1_loser"]) == (6, 2)
    assert (result.loc[0, "set2_winner"], result.loc[0, "set2_loser"]) == (6, 3)


def test_load_local_matches_loads_from_a_local_clone_and_adds_score_features(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_calls = []
    monkeypatch.setattr(
        matches_module.local_sackmann,
        "load_wta_years",
        lambda years, *, local_dir, chronological=False: (
            load_calls.append((list(years), local_dir, chronological)) or _raw_matches()
        ),
    )

    result = load_local_matches(Tour.WTA, [2021], local_dir=tmp_path)

    assert load_calls == [([2021], tmp_path, False)]
    assert result.loc[0, "sets_played"] == 2


def test_load_matches_passes_chronological_through(monkeypatch: pytest.MonkeyPatch) -> None:
    load_calls = []
    monkeypatch.setattr(
        matches_module.atp,
        "load_years",
        lambda years, *, chronological=False: (
            load_calls.append((list(years), chronological)) or _raw_matches()
        ),
    )

    load_matches(Tour.ATP, [2021], chronological=True)

    assert load_calls == [([2021], True)]


def test_load_local_matches_passes_chronological_through(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    load_calls = []
    monkeypatch.setattr(
        matches_module.local_sackmann,
        "load_wta_years",
        lambda years, *, local_dir, chronological=False: (
            load_calls.append((list(years), local_dir, chronological)) or _raw_matches()
        ),
    )

    load_local_matches(Tour.WTA, [2021], local_dir=tmp_path, chronological=True)

    assert load_calls == [([2021], tmp_path, True)]
