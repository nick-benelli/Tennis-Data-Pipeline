"""Tests for Tennis-Data UK tournament summarization."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.handler.uk.cleaner import common
from tennis_data_pipeline.handler.uk.cleaner.tournaments import (
    build_tournament_table,
    build_uk_tournament_table,
)


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


def _clean_match_row(**overrides: object) -> dict:
    row = {
        "tour": "atp",
        "year": 2023,
        "uk_tournament_id": 1,
        "location": "Adelaide",
        "tournament_name": "Adelaide International 1",
        "series": "atp_250",
        "surface": "hard",
        "best_of": 3,
        "is_outdoor": True,
        "match_date": "2023-01-01",
    }
    row.update(overrides)
    row["source_event_key"] = (
        f"{row['year']}_{row['uk_tournament_id']}_"
        f"{common.slugify(str(row['location']))}_{common.slugify(str(row['tournament_name']))}"
    )
    return row


def test_single_tournament_produces_one_row_with_date_range() -> None:
    """All matches for one tournament collapse to a single row with a Start/End date range."""
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
    """Two same-week tournaments sharing a raw id are split apart by Location."""
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
    """A varying attribute is reported as inconsistent, but the mode still fills the row."""
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
    """source_year is derived from the date column when not already present."""
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
    """A pre-existing source_year column is kept as-is, not recomputed from the date."""
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
    """A missing required attribute/key/date column raises KeyError."""
    df = pd.DataFrame([_match_row()]).drop(columns=["Surface"])

    with pytest.raises(KeyError):
        build_tournament_table(df, key_columns=["TournamentNumber", "Location"])


def test_source_event_key_is_carried_through_when_present() -> None:
    """source_event_key (added upstream by common.add_source_event_key) survives into the output."""
    df = pd.DataFrame(
        [
            _match_row(source_event_key="2023_1_adelaide_adelaide_international_1"),
            _match_row(source_event_key="2023_1_adelaide_adelaide_international_1"),
        ]
    )

    tournaments, _ = build_tournament_table(df, key_columns=["TournamentNumber", "Location"])

    assert tournaments.loc[0, "source_event_key"] == "2023_1_adelaide_adelaide_international_1"


def test_source_event_key_column_is_absent_when_not_provided() -> None:
    """Sackmann (and other callers without source_event_key) get no such column, not NaN-filled."""
    df = pd.DataFrame([_match_row()])

    tournaments, _ = build_tournament_table(df, key_columns=["TournamentNumber", "Location"])

    assert "source_event_key" not in tournaments.columns


def test_build_uk_tournament_table_adds_lowercase_location_tournament_key() -> None:
    """location_tournament_key is a lowercase, slugified `{location}_{tournament_name}`."""
    df = pd.DataFrame(
        [
            _clean_match_row(location="'s-Hertogenbosch", tournament_name="Libema Open"),
            _clean_match_row(location="'s-Hertogenbosch", tournament_name="Libema Open"),
        ]
    )

    tournaments, _ = build_uk_tournament_table(df)

    assert tournaments.loc[0, "location_tournament_key"] == "s_hertogenbosch_libema_open"


def test_location_tournament_key_is_stable_across_years_unlike_source_event_key() -> None:
    """Same host+tournament shares a location_tournament_key across years, unlike source_event_key."""
    df = pd.DataFrame(
        [
            _clean_match_row(year=2023, uk_tournament_id=1),
            _clean_match_row(year=2024, uk_tournament_id=1),
        ]
    )

    tournaments, _ = build_uk_tournament_table(df)

    assert tournaments["location_tournament_key"].nunique() == 1
    assert tournaments["source_event_key"].nunique() == 2
