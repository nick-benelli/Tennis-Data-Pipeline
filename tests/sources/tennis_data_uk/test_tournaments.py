"""Tests for Tennis-Data UK tournament summarization."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.sources.tennis_data_uk.tournaments import build_tournament_table


def _match_row(**overrides: object) -> dict:
    row = {
        "TournamentNumber": 1,
        "Location": "Adelaide",
        "Tournament": "Adelaide International 1",
        "Series": "ATP250",
        "Court": "Outdoor",
        "Surface": "Hard",
        "Best of": 3,
        "Date": "2023-01-01",
    }
    row.update(overrides)
    return row


def test_single_tournament_produces_one_row_with_date_range() -> None:
    df = pd.DataFrame(
        [
            _match_row(Date="2023-01-01"),
            _match_row(Date="2023-01-03"),
            _match_row(Date="2023-01-02"),
        ]
    )

    tournaments, inconsistencies = build_tournament_table(
        df, key_columns=["TournamentNumber", "Location"]
    )

    assert len(tournaments) == 1
    assert inconsistencies.empty
    assert tournaments.loc[0, "Start_Date"] == pd.Timestamp("2023-01-01")
    assert tournaments.loc[0, "End_Date"] == pd.Timestamp("2023-01-03")


def test_reused_tournament_number_is_split_by_location() -> None:
    df = pd.DataFrame(
        [
            _match_row(TournamentNumber=58, Location="Stockholm", Tournament="Nordic Open"),
            _match_row(TournamentNumber=58, Location="Tokyo", Tournament="Japan Open"),
        ]
    )

    tournaments, _ = build_tournament_table(df, key_columns=["TournamentNumber", "Location"])

    assert len(tournaments) == 2
    assert sorted(tournaments["Tournament"]) == ["Japan Open", "Nordic Open"]


def test_inconsistent_attribute_is_flagged_but_mode_wins() -> None:
    df = pd.DataFrame(
        [
            _match_row(**{"Best of": 5}),
            _match_row(**{"Best of": 5}),
            _match_row(**{"Best of": 3}),
        ]
    )

    tournaments, inconsistencies = build_tournament_table(
        df, key_columns=["TournamentNumber", "Location"]
    )

    assert len(inconsistencies) == 1
    assert tournaments.loc[0, "Best of"] == 5


def test_source_year_key_is_derived_from_date_when_missing() -> None:
    df = pd.DataFrame(
        [
            _match_row(Date="2023-01-01"),
            _match_row(Date="2024-01-01"),
        ]
    )

    tournaments, _ = build_tournament_table(
        df, key_columns=["source_year", "TournamentNumber", "Location"]
    )

    assert sorted(tournaments["source_year"].tolist()) == [2023, 2024]


def test_existing_source_year_column_is_not_overwritten() -> None:
    df = pd.DataFrame(
        [
            _match_row(Date="2023-01-01", source_year=1999),
        ]
    )

    tournaments, _ = build_tournament_table(
        df, key_columns=["source_year", "TournamentNumber", "Location"]
    )

    assert tournaments.loc[0, "source_year"] == 1999


def test_missing_required_column_raises_key_error() -> None:
    df = pd.DataFrame([_match_row()]).drop(columns=["Surface"])

    with pytest.raises(KeyError):
        build_tournament_table(df, key_columns=["TournamentNumber", "Location"])
