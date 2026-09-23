"""Tests for Pass-1 match-level linking logic (`mapper.matches`)."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.matches import (
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    add_sackmann_match_key,
    attach_tournament_ids,
    build_rank_links,
    classify_rank_candidates,
    generate_rank_candidates,
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
        "match_date": "2025-06-01",
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
        "surface": "clay",
        "tourney_level": "G",
        "tourney_date": "2025-05-25",
        "match_num": 300,
        "winner_id": 111,
        "loser_id": 222,
        "winner_name": "Winner Name",
        "loser_name": "Loser Name",
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


def test_attach_tournament_ids_maps_official_id() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    result = attach_tournament_ids(
        uk_df,
        _tournament_mapper(),
        source="tennis_data_uk",
        match_tournament_col="source_event_key",
        year_col="year",
    )

    assert result["official_tournament_id"].tolist() == [520]
    # original columns untouched, only the new column was added
    assert set(uk_df.columns) <= set(result.columns)


def test_add_sackmann_match_key() -> None:
    sackmann_df = pd.DataFrame([_sk_row(tourney_id="2025-520", match_num=300)])
    result = add_sackmann_match_key(sackmann_df)
    assert result["canonical_match_key"].tolist() == ["2025-520_300"]


def test_build_rank_links_accepts_unique_rank_pair() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert len(accepted) == 1
    assert accepted.iloc[0]["source_match_key"] == "uk_1"
    assert accepted.iloc[0]["canonical_match_key"] == "2025-520_300"
    assert accepted.iloc[0]["match_method"] == MATCH_METHOD_TOURNAMENT_RANK_UNIQUE
    assert not accepted.iloc[0]["review_flag"]
    assert accepted.iloc[0]["winner_id"] == 111
    assert accepted.iloc[0]["loser_id"] == 222
    assert accepted.iloc[0]["round_agrees"]
    assert accepted.iloc[0]["winner_rank_points_diff"] == 0
    assert accepted.iloc[0]["loser_rank_points_diff"] == 0
    assert ambiguous.empty
    assert unmatched.empty


def test_build_rank_links_flags_ambiguous_source_match() -> None:
    """Two Sackmann rows share the same rank pair -> the uk row can't be resolved."""
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame(
        [
            _sk_row(match_num=300),
            _sk_row(match_num=301),
        ]
    )

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert unmatched.empty
    assert set(ambiguous["canonical_match_key"]) == {"2025-520_300", "2025-520_301"}
    assert (ambiguous["source_candidate_count"] == 2).all()
    assert (ambiguous["canonical_candidate_count"] == 1).all()


def test_build_rank_links_flags_ambiguous_canonical_match() -> None:
    """Two uk rows share the same rank pair -> the sackmann row can't be resolved."""
    uk_df = pd.DataFrame(
        [
            _uk_row(source_match_key="uk_1"),
            _uk_row(source_match_key="uk_2"),
        ]
    )
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert unmatched.empty
    assert set(ambiguous["source_match_key"]) == {"uk_1", "uk_2"}
    assert (ambiguous["canonical_candidate_count"] == 2).all()
    assert (ambiguous["source_candidate_count"] == 1).all()


def test_build_rank_links_treats_missing_tournament_mapping_as_unmatched() -> None:
    uk_df = pd.DataFrame([_uk_row(source_event_key="unmapped_event")])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]
    assert pd.isna(unmatched.iloc[0]["official_tournament_id"])


def test_build_rank_links_treats_missing_rank_as_unmatched() -> None:
    uk_df = pd.DataFrame([_uk_row(winner_rank=None)])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]


def test_build_rank_links_raises_on_duplicate_source_match_key() -> None:
    uk_df = pd.DataFrame(
        [
            _uk_row(source_match_key="dup"),
            _uk_row(source_match_key="dup"),
        ]
    )
    sackmann_df = pd.DataFrame([_sk_row()])

    with pytest.raises(ValueError, match="source_match_key"):
        build_rank_links(uk_df, sackmann_df, _tournament_mapper())


def test_build_rank_links_raises_on_duplicate_canonical_match_key() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame(
        [
            _sk_row(tourney_id="2025-520", match_num=300),
            _sk_row(tourney_id="2025-520", match_num=300),
        ]
    )

    with pytest.raises(ValueError, match="canonical_match_key"):
        build_rank_links(uk_df, sackmann_df, _tournament_mapper())


def test_classify_rank_candidates_detects_round_disagreement() -> None:
    candidates = pd.DataFrame(
        [
            {
                "source_match_key": "uk_1",
                "canonical_match_key": "sk_1",
                "round_uk": "F",
                "round_sk": "SF",
                "winner_rank_points_uk": 10000,
                "winner_rank_points_sk": 9800,
                "loser_rank_points_uk": 3000,
                "loser_rank_points_sk": 3000,
            }
        ]
    )

    result = classify_rank_candidates(candidates)

    assert result.iloc[0]["is_unique"]
    assert not result.iloc[0]["round_agrees"]
    assert result.iloc[0]["winner_rank_points_diff"] == 200
    assert result.iloc[0]["loser_rank_points_diff"] == 0


def test_generate_rank_candidates_excludes_rows_without_official_tournament_id() -> None:
    uk_linked = pd.DataFrame([{**_uk_row(), "official_tournament_id": pd.NA}])
    sackmann_linked = pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])

    candidates = generate_rank_candidates(uk_linked, sackmann_linked)

    assert candidates.empty
