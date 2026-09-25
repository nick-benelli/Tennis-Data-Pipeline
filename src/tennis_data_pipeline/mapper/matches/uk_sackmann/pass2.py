"""Pass 2: tournament + round blocked, deterministic winner/loser name-pair linking."""

from __future__ import annotations

import pandas as pd

from .names import player_name_compatible
from .schema import (
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
    NAME_PAIR_CROSSWALK_COLUMNS,
    NAME_PAIR_KEY_COLUMNS,
)


def _rank_agrees(uk_rank: pd.Series, sackmann_rank: pd.Series) -> pd.Series:
    """Nullable-bool: True/False if both ranks are present, else NA (missing)."""
    both_present = uk_rank.notna() & sackmann_rank.notna()
    agrees = pd.Series(pd.NA, index=uk_rank.index, dtype="boolean")
    agrees[both_present] = uk_rank[both_present] == sackmann_rank[both_present]
    return agrees


def generate_name_pair_candidates(
    uk_residual: pd.DataFrame, sackmann_residual: pd.DataFrame
) -> pd.DataFrame:
    """Generate Pass-2 candidates: tournament + round block, then name-pair filter.

    Both inputs must already carry `official_tournament_id`; rows missing it
    are excluded (e.g. Laver Cup/United Cup/Next Gen Finals, which never got a
    `official_tournament_id` in the first place). `sackmann_residual` must
    carry `canonical_match_key`.

    Winner/loser orientation is never swapped: a row survives only if the
    source winner name is compatible with the canonical *winner* name, and
    likewise for losers.
    """
    uk_blockable = uk_residual.dropna(subset=["official_tournament_id"]).copy()
    sackmann_blockable = sackmann_residual.dropna(subset=["official_tournament_id"]).copy()
    sackmann_blockable["year"] = sackmann_blockable["source_year"]

    candidates = uk_blockable.merge(
        sackmann_blockable,
        on=NAME_PAIR_KEY_COLUMNS,
        how="inner",
        suffixes=("_uk", "_sk"),
    )
    if candidates.empty:
        return candidates

    compatible = candidates.apply(
        lambda row: (
            player_name_compatible(row["winner_name_uk"], row["winner_name_sk"])
            and player_name_compatible(row["loser_name_uk"], row["loser_name_sk"])
        ),
        axis=1,
    )
    return candidates.loc[compatible].copy()


def classify_name_pair_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    """Add uniqueness + data-quality diagnostics to Pass-2 name-pair candidates.

    Same `source_candidate_count`/`canonical_candidate_count`/`is_unique`
    pattern as `classify_rank_candidates`. `round_agrees` is always True (it's
    a hard block by construction); `winner_rank_agrees`/`loser_rank_agrees`
    are nullable bools (NA when a rank is missing on either side).
    """
    candidates = candidates.copy()
    if candidates.empty:
        for col in (
            "source_candidate_count",
            "canonical_candidate_count",
            "is_unique",
            "round_agrees",
            "winner_rank_agrees",
            "loser_rank_agrees",
        ):
            candidates[col] = pd.Series(dtype="object")
        return candidates

    candidates["source_candidate_count"] = candidates.groupby("source_match_key")[
        "canonical_match_key"
    ].transform("nunique")
    candidates["canonical_candidate_count"] = candidates.groupby("canonical_match_key")[
        "source_match_key"
    ].transform("nunique")
    candidates["is_unique"] = candidates["source_candidate_count"].eq(1) & candidates[
        "canonical_candidate_count"
    ].eq(1)

    candidates["round_agrees"] = True
    candidates["winner_rank_agrees"] = _rank_agrees(
        candidates["winner_rank_uk"], candidates["winner_rank_sk"]
    )
    candidates["loser_rank_agrees"] = _rank_agrees(
        candidates["loser_rank_uk"], candidates["loser_rank_sk"]
    )

    return candidates


def _data_quality_flag(candidates: pd.DataFrame) -> pd.Series:
    """ "rank_mismatch" if either rank disagrees, "missing_rank" if either is unknown, else NA."""
    winner_agrees = candidates["winner_rank_agrees"]
    loser_agrees = candidates["loser_rank_agrees"]
    mismatch = (winner_agrees == False) | (loser_agrees == False)  # noqa: E712 (nullable boolean)
    missing = winner_agrees.isna() | loser_agrees.isna()

    flag = pd.Series(pd.NA, index=candidates.index, dtype="object")
    flag = flag.mask(missing.fillna(False), "missing_rank")
    flag = flag.mask(mismatch.fillna(False), "rank_mismatch")
    return flag


def build_name_pair_links(
    uk_residual: pd.DataFrame, sackmann_residual: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Pass 2 (tournament + round blocked, deterministic name pair) end to end.

    `uk_residual`/`sackmann_residual` are expected to be Pass-1 leftovers
    (e.g. `build_rank_links`'s `unmatched_uk_rows`, and Sackmann rows whose
    `canonical_match_key` isn't in Pass 1's accepted links) - see
    `build_rank_and_name_links` for the full two-pass pipeline.

    Returns `(accepted_links, ambiguous_candidates, unmatched_uk_rows)` in the
    same shape as `build_rank_links`. `accepted_links` uses
    `NAME_PAIR_CROSSWALK_COLUMNS`, `match_method` is always
    `MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR`, and `data_quality_flag`
    records whether the ranks disagreed/were missing despite the otherwise
    unambiguous name-pair match (`review_flag` is reserved for linkage
    ambiguity, not data-quality issues - it's always False here since only
    unique candidates are ever accepted).

    Raises `ValueError` if `source_match_key` isn't unique in `uk_residual`, or
    `canonical_match_key` isn't unique in `sackmann_residual` - same guard as
    `build_rank_links`, since this may run on residual data reloaded from disk
    rather than data freshly derived in-process.

    Raises `AssertionError` if an accepted link isn't 1:1 on both match keys.
    """
    if uk_residual["source_match_key"].duplicated().any():
        raise ValueError("uk_residual['source_match_key'] must be unique")
    if sackmann_residual["canonical_match_key"].duplicated().any():
        raise ValueError("sackmann_residual['canonical_match_key'] must be unique")

    candidates = classify_name_pair_candidates(
        generate_name_pair_candidates(uk_residual, sackmann_residual)
    )

    accepted = candidates.loc[candidates["is_unique"]].copy()
    accepted["match_method"] = MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR
    accepted["review_flag"] = False
    accepted["data_quality_flag"] = _data_quality_flag(accepted)
    if (
        accepted["source_match_key"].duplicated().any()
        or accepted["canonical_match_key"].duplicated().any()
    ):
        raise AssertionError("accepted name-pair links must be 1:1 on both match keys")
    accepted = accepted[NAME_PAIR_CROSSWALK_COLUMNS]

    ambiguous = candidates.loc[~candidates["is_unique"]].copy()

    unmatched_uk_rows = uk_residual.loc[
        ~uk_residual["source_match_key"].isin(candidates["source_match_key"])
    ].copy()

    return accepted, ambiguous, unmatched_uk_rows
