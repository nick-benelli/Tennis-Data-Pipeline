"""Pass 1: tournament-blocked exact rank-pair match linking (`build_rank_links`)."""

from __future__ import annotations

import pandas as pd

from .schema import CROSSWALK_COLUMNS, MATCH_METHOD_TOURNAMENT_RANK_UNIQUE, RANK_CANDIDATE_KEY_COLUMNS
from .tournament_ids import attach_tournament_ids


def add_sackmann_match_key(sackmann_df: pd.DataFrame) -> pd.DataFrame:
    """Add a stable `canonical_match_key` = `tourney_id` + "_" + `match_num` column.

    A no-op if `canonical_match_key` is already present - `datasources.sackmann.cleaning`
    attaches it during `clean_matches`, so this is only a fallback for uncleaned input.
    Mirrors that function's round-robin disambiguation (append `round` only for
    rows whose plain `tourney_id_match_num` key collides) - see its docstring.
    """
    if "canonical_match_key" in sackmann_df.columns:
        return sackmann_df
    sackmann_df = sackmann_df.copy()
    key = sackmann_df["tourney_id"].astype(str) + "_" + sackmann_df["match_num"].astype(str)
    collides = key.duplicated(keep=False)
    if collides.any():
        key = key.where(~collides, key + "_" + sackmann_df["round"].astype(str))
    sackmann_df["canonical_match_key"] = key
    return sackmann_df


def _attach_uk(uk_df: pd.DataFrame, tournament_mapper_df: pd.DataFrame) -> pd.DataFrame:
    return attach_tournament_ids(
        uk_df,
        tournament_mapper_df,
        source="tennis_data_uk",
        match_tournament_col="source_event_key",
        year_col="year",
    )


def _attach_sackmann(sackmann_df: pd.DataFrame, tournament_mapper_df: pd.DataFrame) -> pd.DataFrame:
    return attach_tournament_ids(
        sackmann_df,
        tournament_mapper_df,
        source="sackmann",
        match_tournament_col="tourney_id",
        year_col="source_year",
    )


def generate_rank_candidates(uk_df: pd.DataFrame, sackmann_df: pd.DataFrame) -> pd.DataFrame:
    """Generate match-link candidates by blocking on tournament + exact rank pair.

    Both inputs must already carry `official_tournament_id` (see
    `attach_tournament_ids`); `sackmann_df` gets `canonical_match_key` added if
    missing. Rows missing `official_tournament_id`, `winner_rank`, or
    `loser_rank` are excluded on both sides - they can't be rank-matched.

    This is a plain vectorized inner merge, so a source row can legitimately
    appear against more than one Sackmann row (and vice versa); resolving
    that ambiguity is `classify_rank_candidates`'s job, not this one.
    """
    if "canonical_match_key" not in sackmann_df.columns:
        sackmann_df = add_sackmann_match_key(sackmann_df)

    uk_ranked = uk_df.dropna(subset=["official_tournament_id", "winner_rank", "loser_rank"]).copy()
    sackmann_ranked = sackmann_df.dropna(
        subset=["official_tournament_id", "winner_rank", "loser_rank"]
    ).copy()
    sackmann_ranked["year"] = sackmann_ranked["source_year"]

    for frame in (uk_ranked, sackmann_ranked):
        frame["winner_rank"] = frame["winner_rank"].astype("Int64")
        frame["loser_rank"] = frame["loser_rank"].astype("Int64")

    return uk_ranked.merge(
        sackmann_ranked,
        on=RANK_CANDIDATE_KEY_COLUMNS,
        how="inner",
        suffixes=("_uk", "_sk"),
    )


def classify_rank_candidates(candidates: pd.DataFrame) -> pd.DataFrame:
    """Add uniqueness + supporting-evidence diagnostics to rank-pair candidates.

    - `source_candidate_count` / `canonical_candidate_count`: how many
      counterpart rows each side's match key maps to among these candidates.
    - `is_unique`: True only when both counts equal 1 - the sole condition
      under which a candidate is safe to accept.
    - `round_agrees`, `winner_rank_points_diff`, `loser_rank_points_diff`:
      corroborating evidence only; they never filter/reject a candidate here.
    """
    candidates = candidates.copy()

    candidates["source_candidate_count"] = candidates.groupby("source_match_key")[
        "canonical_match_key"
    ].transform("nunique")
    candidates["canonical_candidate_count"] = candidates.groupby("canonical_match_key")[
        "source_match_key"
    ].transform("nunique")
    candidates["is_unique"] = candidates["source_candidate_count"].eq(1) & candidates[
        "canonical_candidate_count"
    ].eq(1)

    # round_uk/round_sk are each `category` dtype from their own source with
    # independently-built category sets - comparing two Categoricals directly
    # raises unless the categories match exactly, so compare as plain objects
    # instead (preserves NaN != NaN; only the dtype changes).
    candidates["round_agrees"] = candidates["round_uk"].astype(object) == candidates["round_sk"].astype(
        object
    )
    candidates["winner_rank_points_diff"] = (
        candidates["winner_rank_points_uk"] - candidates["winner_rank_points_sk"]
    ).abs()
    candidates["loser_rank_points_diff"] = (
        candidates["loser_rank_points_uk"] - candidates["loser_rank_points_sk"]
    ).abs()

    return candidates


def build_rank_links(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    tournament_mapper_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Pass 1 (tournament-blocked exact rank pair) match linking end to end.

    Returns `(accepted_links, ambiguous_candidates, unmatched_uk_rows)`:

    - `accepted_links`: the `CROSSWALK_COLUMNS` crosswalk - one row per
      uk<->sackmann pair, `source_match_key` and `canonical_match_key` are
      each unique across the frame, `match_method` is always
      `MATCH_METHOD_TOURNAMENT_RANK_UNIQUE`.
    - `ambiguous_candidates`: classified candidates where either side matched
      more than one counterpart - kept for a later resolution pass, never
      silently dropped.
    - `unmatched_uk_rows`: `uk_df` rows (identified by `source_match_key`)
      that produced no rank-pair candidate at all, e.g. missing tournament
      id, missing rank, or no counterpart Sackmann row.

    Raises `ValueError` if `source_match_key` isn't unique in `uk_df`, or the
    derived `canonical_match_key` isn't unique in `sackmann_df`.
    """
    if uk_df["source_match_key"].duplicated().any():
        raise ValueError("uk_df['source_match_key'] must be unique")

    sackmann_df = add_sackmann_match_key(sackmann_df)
    if sackmann_df["canonical_match_key"].duplicated().any():
        raise ValueError("sackmann_df's derived canonical_match_key must be unique")

    uk_linked = _attach_uk(uk_df, tournament_mapper_df)
    sackmann_linked = _attach_sackmann(sackmann_df, tournament_mapper_df)

    candidates = classify_rank_candidates(generate_rank_candidates(uk_linked, sackmann_linked))

    accepted = candidates.loc[candidates["is_unique"]].copy()
    accepted["match_method"] = MATCH_METHOD_TOURNAMENT_RANK_UNIQUE
    accepted["review_flag"] = False
    if (
        accepted["source_match_key"].duplicated().any()
        or accepted["canonical_match_key"].duplicated().any()
    ):
        raise AssertionError("accepted rank links must be 1:1 on both match keys")
    accepted = accepted[CROSSWALK_COLUMNS]

    ambiguous = candidates.loc[~candidates["is_unique"]].copy()

    unmatched_uk_rows = uk_linked.loc[
        ~uk_linked["source_match_key"].isin(candidates["source_match_key"])
    ].copy()

    return accepted, ambiguous, unmatched_uk_rows
