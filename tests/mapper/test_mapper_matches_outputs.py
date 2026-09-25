"""Tests for the formalized per-year output builders (`mapper.matches.uk_sackmann.outputs`)."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.matches import (
    ENRICHED_LINKAGE_BLOCK_COLUMNS,
    MATCH_METHOD_MANUAL,
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
    add_unmatched_diagnostics,
    build_enriched_matches,
    build_linkage_summary,
    build_match_crosswalk,
    finalize_link_status,
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
        "round": "F",
        "source_year": 2025,
        "tour": "atp",
        "canonical_match_key": "2025-520_300",
    }
    row.update(overrides)
    return row


def _accepted_row(**overrides: object) -> dict:
    row: dict = {
        "year": 2025,
        "tour": "atp",
        "source_match_key": "uk_1",
        "canonical_match_key": "2025-520_300",
        "official_tournament_id": 520,
        "winner_id": 111,
        "loser_id": 222,
        "match_method": MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
        "review_flag": False,
        "source_candidate_count": 1,
        "canonical_candidate_count": 1,
        "round_agrees": True,
        "winner_rank_points_diff": 0,
        "loser_rank_points_diff": 0,
    }
    row.update(overrides)
    return row


# --------------------------------------------------------------------------- #
# build_match_crosswalk
# --------------------------------------------------------------------------- #


def test_build_match_crosswalk_one_row_per_accepted_link() -> None:
    accepted = pd.DataFrame(
        [_accepted_row(), _accepted_row(source_match_key="uk_2", canonical_match_key="2025-520_301")]
    )

    crosswalk = build_match_crosswalk(accepted)

    assert len(crosswalk) == 2
    assert crosswalk["source_match_key"].tolist() == ["uk_1", "uk_2"]
    # Pass-2-only columns are present (NA) even though this batch is all Pass 1.
    assert "data_quality_flag" in crosswalk.columns


def test_build_match_crosswalk_raises_on_duplicate_source_key() -> None:
    accepted = pd.DataFrame([_accepted_row(), _accepted_row(canonical_match_key="2025-520_301")])

    with pytest.raises(ValueError, match="source_match_key"):
        build_match_crosswalk(accepted)


def test_build_match_crosswalk_includes_year_and_tour() -> None:
    crosswalk = build_match_crosswalk(pd.DataFrame([_accepted_row()]))

    assert crosswalk.loc[0, "year"] == 2025
    assert crosswalk.loc[0, "tour"] == "atp"


def test_build_match_crosswalk_raises_on_duplicate_canonical_key() -> None:
    accepted = pd.DataFrame([_accepted_row(), _accepted_row(source_match_key="uk_2")])

    with pytest.raises(ValueError, match="canonical_match_key"):
        build_match_crosswalk(accepted)


# --------------------------------------------------------------------------- #
# build_enriched_matches
# --------------------------------------------------------------------------- #


def test_build_enriched_matches_preserves_all_source_rows() -> None:
    uk_df = pd.DataFrame([_uk_row(source_match_key="uk_1"), _uk_row(source_match_key="uk_2")])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame([_accepted_row()])  # only uk_1 is linked

    enriched = build_enriched_matches(uk_df, sackmann_df, accepted)

    assert len(enriched) == len(uk_df) == 2


def test_build_enriched_matches_linked_rows_get_canonical_ids() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame([_accepted_row()])

    enriched = build_enriched_matches(uk_df, sackmann_df, accepted)

    row = enriched.iloc[0]
    assert row["canonical_match_key"] == "2025-520_300"
    assert row["canonical_winner_id"] == 111
    assert row["canonical_winner_name"] == "Taylor Fritz"
    assert row["canonical_loser_name"] == "Emilio Nava"
    assert row["canonical_tourney_name"] == "Roland Garros"


def test_build_enriched_matches_unmatched_rows_have_null_canonical_ids() -> None:
    uk_df = pd.DataFrame([_uk_row(source_match_key="uk_unmatched")])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame(columns=list(_accepted_row().keys()))  # nothing linked

    enriched = build_enriched_matches(uk_df, sackmann_df, accepted)

    row = enriched.iloc[0]
    assert pd.isna(row["canonical_match_key"])
    assert pd.isna(row["canonical_winner_id"])
    assert pd.isna(row["canonical_winner_name"])


def test_build_enriched_matches_raises_if_winner_id_disagrees_with_canonical_match() -> None:
    """An accepted row whose winner_id doesn't match its canonical_match_key's Sackmann
    row is a construction bug, not a real match - must fail loudly."""
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])  # winner_id=111
    accepted = pd.DataFrame([_accepted_row(winner_id=999)])  # disagrees with sackmann_df

    with pytest.raises(AssertionError, match="winner_id/loser_id"):
        build_enriched_matches(uk_df, sackmann_df, accepted)


def test_build_enriched_matches_appends_linkage_block_in_fixed_order() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame([_accepted_row()])

    enriched = build_enriched_matches(uk_df, sackmann_df, accepted)

    assert list(enriched.columns) == [*uk_df.columns, *ENRICHED_LINKAGE_BLOCK_COLUMNS]


# --------------------------------------------------------------------------- #
# finalize_link_status
# --------------------------------------------------------------------------- #


def test_finalize_link_status_preserves_multiple_ambiguous_candidates() -> None:
    """A source row with two candidates keeps both rows in the ambiguous output."""
    accepted = pd.DataFrame(columns=["source_match_key", "canonical_match_key"])
    ambiguous = pd.DataFrame(
        [
            {"source_match_key": "uk_1", "canonical_match_key": "sk_a"},
            {"source_match_key": "uk_1", "canonical_match_key": "sk_b"},
        ]
    )
    unmatched = pd.DataFrame(columns=["source_match_key"])

    ambiguous_final, unmatched_final = finalize_link_status(accepted, ambiguous, unmatched)

    assert len(ambiguous_final) == 2
    assert unmatched_final.empty


def test_finalize_link_status_removes_rows_resolved_by_later_pass() -> None:
    """A row that was Pass-1-ambiguous but got accepted by Pass 2 drops out of ambiguous."""
    accepted = pd.DataFrame([_accepted_row(match_method=MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR)])
    ambiguous = pd.DataFrame(
        [
            {"source_match_key": "uk_1", "canonical_match_key": "sk_other"},
            {"source_match_key": "uk_2", "canonical_match_key": "sk_x"},
        ]
    )
    unmatched = pd.DataFrame(columns=["source_match_key"])

    ambiguous_final, unmatched_final = finalize_link_status(accepted, ambiguous, unmatched)

    assert ambiguous_final["source_match_key"].tolist() == ["uk_2"]
    assert unmatched_final.empty


def test_finalize_link_status_unmatched_excludes_resolved_or_ambiguous_keys() -> None:
    """Only rows still unmatched after accounting for accepted+ambiguous survive."""
    accepted = pd.DataFrame([_accepted_row()])  # uk_1 linked
    ambiguous = pd.DataFrame([{"source_match_key": "uk_2", "canonical_match_key": "sk_x"}])
    unmatched = pd.DataFrame(
        [
            {"source_match_key": "uk_1"},  # resolved by Pass 2 elsewhere - must be dropped
            {"source_match_key": "uk_2"},  # still ambiguous - must be dropped from unmatched
            {"source_match_key": "uk_3"},  # genuinely unmatched - must remain
        ]
    )

    _, unmatched_final = finalize_link_status(accepted, ambiguous, unmatched)

    assert unmatched_final["source_match_key"].tolist() == ["uk_3"]


# --------------------------------------------------------------------------- #
# add_unmatched_diagnostics
# --------------------------------------------------------------------------- #


def test_add_unmatched_diagnostics_classifies_missing_tournament() -> None:
    unmatched = pd.DataFrame([_uk_row(source_match_key="uk_1", official_tournament_id=pd.NA)])

    result = add_unmatched_diagnostics(unmatched)

    assert result.loc[0, "linkage_status"] == "unmatched"
    assert result.loc[0, "unmatched_reason"] == "missing_tournament_mapping"


def test_add_unmatched_diagnostics_classifies_missing_rank() -> None:
    unmatched = pd.DataFrame(
        [_uk_row(source_match_key="uk_1", official_tournament_id=520, winner_rank=pd.NA)]
    )

    result = add_unmatched_diagnostics(unmatched)

    assert result.loc[0, "unmatched_reason"] == "no_rank_candidate"


def test_add_unmatched_diagnostics_classifies_no_name_pair_candidate() -> None:
    unmatched = pd.DataFrame([_uk_row(source_match_key="uk_1", official_tournament_id=520)])

    result = add_unmatched_diagnostics(unmatched)

    assert result.loc[0, "unmatched_reason"] == "no_name_pair_candidate"


# --------------------------------------------------------------------------- #
# build_linkage_summary
# --------------------------------------------------------------------------- #


def test_build_linkage_summary_counts_pass1_and_pass2_separately() -> None:
    uk_df = pd.DataFrame([_uk_row(source_match_key=f"uk_{i}") for i in range(4)])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame(
        [
            _accepted_row(source_match_key="uk_1", match_method=MATCH_METHOD_TOURNAMENT_RANK_UNIQUE),
            _accepted_row(
                source_match_key="uk_2",
                canonical_match_key="2025-520_301",
                match_method=MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
            ),
        ]
    )
    ambiguous = pd.DataFrame([{"source_match_key": "uk_3", "canonical_match_key": "sk_x"}])
    unmatched = pd.DataFrame([{"source_match_key": "uk_4"}])

    summary = build_linkage_summary(
        uk_df, sackmann_df, accepted, ambiguous, unmatched, year=2025, tour="atp"
    )

    row = summary.iloc[0]
    assert row["uk_total_matches"] == 4
    assert row["sackmann_total_matches"] == 1
    assert row["linked_matches"] == 2
    assert row["linked_manual"] == 0
    assert row["linked_pass_1"] == 1
    assert row["linked_pass_2"] == 1
    assert row["ambiguous_matches"] == 1
    assert row["unmatched_matches"] == 1


def test_build_linkage_summary_counts_manual_separately() -> None:
    uk_df = pd.DataFrame([_uk_row(source_match_key=f"uk_{i}") for i in range(2)])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame(
        [
            _accepted_row(source_match_key="uk_1", match_method=MATCH_METHOD_MANUAL),
            _accepted_row(source_match_key="uk_2", match_method=MATCH_METHOD_TOURNAMENT_RANK_UNIQUE),
        ]
    )
    ambiguous = pd.DataFrame(columns=["source_match_key", "canonical_match_key"])
    unmatched = pd.DataFrame(columns=["source_match_key"])

    summary = build_linkage_summary(
        uk_df, sackmann_df, accepted, ambiguous, unmatched, year=2025, tour="atp"
    )

    row = summary.iloc[0]
    assert row["linked_manual"] == 1
    assert row["linked_pass_1"] == 1


def test_build_linkage_summary_leaves_linked_at_na() -> None:
    """linked_at is populated by the workflow layer, not this pure function."""
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame([_accepted_row()])
    ambiguous = pd.DataFrame(columns=["source_match_key", "canonical_match_key"])
    unmatched = pd.DataFrame(columns=["source_match_key"])

    summary = build_linkage_summary(
        uk_df, sackmann_df, accepted, ambiguous, unmatched, year=2025, tour="atp"
    )

    assert "linked_at" in summary.columns
    assert pd.isna(summary.iloc[0]["linked_at"])


def test_build_linkage_summary_does_not_double_count_ambiguous_candidate_rows() -> None:
    """Two candidate rows for the same source match count as one ambiguous match."""
    uk_df = pd.DataFrame([_uk_row(source_match_key="uk_1")])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame(columns=list(_accepted_row().keys()))
    ambiguous = pd.DataFrame(
        [
            {"source_match_key": "uk_1", "canonical_match_key": "sk_a"},
            {"source_match_key": "uk_1", "canonical_match_key": "sk_b"},
        ]
    )
    unmatched = pd.DataFrame(columns=["source_match_key"])

    summary = build_linkage_summary(
        uk_df, sackmann_df, accepted, ambiguous, unmatched, year=2025, tour="atp"
    )

    assert summary.iloc[0]["ambiguous_matches"] == 1


def test_build_linkage_summary_raises_on_reconciliation_mismatch() -> None:
    uk_df = pd.DataFrame([_uk_row(source_match_key="uk_1"), _uk_row(source_match_key="uk_2")])
    sackmann_df = pd.DataFrame([_sk_row()])
    accepted = pd.DataFrame(columns=list(_accepted_row().keys()))
    ambiguous = pd.DataFrame(columns=["source_match_key", "canonical_match_key"])
    unmatched = pd.DataFrame([{"source_match_key": "uk_1"}])  # uk_2 missing entirely

    with pytest.raises(AssertionError):
        build_linkage_summary(uk_df, sackmann_df, accepted, ambiguous, unmatched, year=2025, tour="atp")
