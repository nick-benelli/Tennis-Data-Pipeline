"""Tests for Pass 0 (`mapper.matches.build_manual_links`/`build_manual_rank_and_name_links`)."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.matches import (
    MATCH_METHOD_MANUAL,
    build_manual_links,
    build_manual_rank_and_name_links,
)


def _tournament_mapper() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "official_tournament_id": 520,
                "year": 2025,
                "source": "tennis_data_uk",
                "source_tournament_id": "2025_29_paris_french_open",
            },
            {
                "official_tournament_id": 520,
                "year": 2025,
                "source": "sackmann",
                "source_tournament_id": "2025-520",
            },
        ]
    )


def _uk_row(**overrides: object) -> dict:
    row: dict = {
        "source": "tennis_data_uk",
        "tour": "atp",
        "year": 2025,
        "source_event_key": "2025_29_paris_french_open",
        "tournament_name": "French Open",
        "winner_name": "Fritz T.",
        "loser_name": "Nava E.",
        "winner_rank": 1,
        "loser_rank": 5,
        "winner_rank_points": 10000,
        "loser_rank_points": 3000,
        "round": "F",
        "source_match_key": "uk_1",
    }
    row.update(overrides)
    return row


def _sk_row(**overrides: object) -> dict:
    row: dict = {
        "tourney_id": "2025-520",
        "tourney_name": "Roland Garros",
        "match_num": 300,
        "winner_id": 111,
        "loser_id": 222,
        "winner_name": "Taylor Fritz",
        "loser_name": "Emilio Nava",
        "winner_rank": 1,
        "loser_rank": 5,
        "winner_rank_points": 10000,
        "loser_rank_points": 3000,
        "round": "F",
        "source_year": 2025,
        "tour": "atp",
    }
    row.update(overrides)
    return row


def _manual_link(**overrides: object) -> dict:
    row: dict = {"year": 2025, "source_match_key": "uk_1", "canonical_match_key": "2025-520_300"}
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# build_manual_links
# --------------------------------------------------------------------------- #


def test_build_manual_links_empty_manual_links_df_returns_empty_crosswalk() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame(columns=["year", "source_match_key", "canonical_match_key"])

    result = build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)

    assert result.empty


def test_build_manual_links_resolves_matched_pair() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame([_manual_link()])

    result = build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["source_match_key"] == "uk_1"
    assert row["canonical_match_key"] == "2025-520_300"
    assert row["official_tournament_id"] == 520
    assert row["winner_id"] == 111
    assert row["loser_id"] == 222
    assert row["match_method"] == MATCH_METHOD_MANUAL
    assert bool(row["review_flag"]) is False
    assert pd.isna(row["source_candidate_count"])
    assert pd.isna(row["round_agrees"])


def test_build_manual_links_raises_on_unknown_source_match_key() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame([_manual_link(source_match_key="uk_does_not_exist")])

    with pytest.raises(ValueError, match="unknown source_match_key"):
        build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)


def test_build_manual_links_raises_on_unknown_canonical_match_key() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame([_manual_link(canonical_match_key="2025-520_999")])

    with pytest.raises(ValueError, match="unknown canonical_match_key"):
        build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)


def test_build_manual_links_raises_on_duplicate_source_match_key() -> None:
    uk_df = pd.DataFrame([_uk_row(), _uk_row(source_match_key="uk_2")])
    sackmann_df = pd.DataFrame([_sk_row(), _sk_row(match_num=301)])
    manual_links_df = pd.DataFrame(
        [
            _manual_link(),
            _manual_link(canonical_match_key="2025-520_301"),
        ]
    )

    with pytest.raises(ValueError, match="source_match_key"):
        build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)


def test_build_manual_links_ignores_rows_for_other_years() -> None:
    """A manual-links file spanning many seasons shouldn't error on this year's call
    just because it also has (perfectly valid) rows for a different year."""
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame(
        [
            _manual_link(year=2024, source_match_key="uk_from_2024", canonical_match_key="2024-1_1"),
            _manual_link(),
        ]
    )

    result = build_manual_links(uk_df, sackmann_df, _tournament_mapper(), manual_links_df)

    assert len(result) == 1
    assert result.iloc[0]["source_match_key"] == "uk_1"


# --------------------------------------------------------------------------- #
# build_manual_rank_and_name_links
# --------------------------------------------------------------------------- #


def test_build_manual_rank_and_name_links_removes_manual_rows_from_pass1_pool() -> None:
    """A manually-linked row must not be reconsidered by Pass 1, even if it would
    otherwise be part of a rank-pair ambiguity."""
    uk_df = pd.DataFrame([_uk_row()])
    # Two Sackmann rows share the same rank pair - would be ambiguous in Pass 1
    # if the manual link hadn't already removed `uk_1` from the pool.
    sackmann_df = pd.DataFrame([_sk_row(match_num=300), _sk_row(match_num=301)])
    manual_links_df = pd.DataFrame([_manual_link(canonical_match_key="2025-520_300")])

    accepted, ambiguous, unmatched = build_manual_rank_and_name_links(
        uk_df, sackmann_df, _tournament_mapper(), manual_links_df
    )

    assert len(accepted) == 1
    assert accepted.iloc[0]["match_method"] == MATCH_METHOD_MANUAL
    assert accepted.iloc[0]["canonical_match_key"] == "2025-520_300"
    assert "uk_1" not in set(ambiguous.get("source_match_key", []))
    assert "uk_1" not in set(unmatched.get("source_match_key", []))


def test_build_manual_rank_and_name_links_with_no_manual_links_matches_pass1_2_only() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    manual_links_df = pd.DataFrame(columns=["year", "source_match_key", "canonical_match_key"])

    accepted, _ambiguous, _unmatched = build_manual_rank_and_name_links(
        uk_df, sackmann_df, _tournament_mapper(), manual_links_df
    )

    assert len(accepted) == 1
    assert accepted.iloc[0]["match_method"] != MATCH_METHOD_MANUAL
