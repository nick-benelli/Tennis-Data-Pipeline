"""Pass 0: hand-maintained manual match overrides (`build_manual_links`).

Resolved before Pass 1/2 (see `pipeline.build_manual_rank_and_name_links`) so a
manually-confirmed pair is removed from both sides' candidate pools up front -
the algorithmic passes never see it and so can never claim it for a
different, possibly wrong, match.
"""

from __future__ import annotations

import pandas as pd

from .pass1 import _attach_sackmann, _attach_uk, add_sackmann_match_key
from .schema import CROSSWALK_COLUMNS, MATCH_METHOD_MANUAL

_UK_JOIN_COLUMNS = [
    "source_match_key",
    "official_tournament_id",
    "year",
    "tour",
    "winner_rank",
    "loser_rank",
]
_SACKMANN_JOIN_COLUMNS = ["canonical_match_key", "winner_id", "loser_id"]

# Diagnostic-only CROSSWALK_COLUMNS fields that don't apply to a manual
# override - there's no candidate pool to count or compare against.
_NA_DIAGNOSTIC_COLUMNS = (
    "source_candidate_count",
    "canonical_candidate_count",
    "round_agrees",
    "winner_rank_points_diff",
    "loser_rank_points_diff",
)


def build_manual_links(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    tournament_mapper_df: pd.DataFrame,
    manual_links_df: pd.DataFrame,
) -> pd.DataFrame:
    """Resolve a hand-maintained `(source_match_key, canonical_match_key)` override table.

    `manual_links_df` is first filtered to rows whose `year` matches one of
    `uk_df["year"]`'s values - the file may accumulate entries for many
    seasons, but `uk_df`/`sackmann_df` here are always one season's worth, so
    any other-year rows are simply not this call's concern.

    Every remaining key must exist in `uk_df`/`sackmann_df` - unlike Pass 1/2,
    an unresolvable manual link is a data-entry error, not a "no match", so it
    raises rather than being silently dropped.

    Returns the `CROSSWALK_COLUMNS` crosswalk shape, `match_method` always
    `MATCH_METHOD_MANUAL`. Diagnostic columns that don't apply to a manual
    override (candidate counts, round/rank-points agreement) are NA.

    Raises `ValueError` if `uk_df['source_match_key']`, the derived
    `sackmann_df['canonical_match_key']`, or `manual_links_df`'s own
    `source_match_key`/`canonical_match_key` aren't each unique, or if
    `manual_links_df` references a key missing from `uk_df`/`sackmann_df`.
    """
    if manual_links_df.empty:
        return pd.DataFrame(columns=CROSSWALK_COLUMNS)

    manual_links_df = manual_links_df.loc[manual_links_df["year"].isin(uk_df["year"].unique())]
    if manual_links_df.empty:
        return pd.DataFrame(columns=CROSSWALK_COLUMNS)

    if uk_df["source_match_key"].duplicated().any():
        raise ValueError("uk_df['source_match_key'] must be unique")
    sackmann_df = add_sackmann_match_key(sackmann_df)
    if sackmann_df["canonical_match_key"].duplicated().any():
        raise ValueError("sackmann_df's derived canonical_match_key must be unique")

    if manual_links_df["source_match_key"].duplicated().any():
        raise ValueError("manual_links_df['source_match_key'] must be unique")
    if manual_links_df["canonical_match_key"].duplicated().any():
        raise ValueError("manual_links_df['canonical_match_key'] must be unique")

    missing_uk = sorted(set(manual_links_df["source_match_key"]) - set(uk_df["source_match_key"]))
    missing_sackmann = sorted(
        set(manual_links_df["canonical_match_key"]) - set(sackmann_df["canonical_match_key"])
    )
    if missing_uk or missing_sackmann:
        raise ValueError(
            f"manual_links_df references unknown source_match_key(s) {missing_uk} and/or "
            f"unknown canonical_match_key(s) {missing_sackmann}"
        )

    uk_linked = _attach_uk(uk_df, tournament_mapper_df)
    sackmann_linked = _attach_sackmann(sackmann_df, tournament_mapper_df)

    accepted = manual_links_df[["source_match_key", "canonical_match_key"]].merge(
        uk_linked[_UK_JOIN_COLUMNS], on="source_match_key", how="left", validate="one_to_one"
    )
    accepted = accepted.merge(
        sackmann_linked[_SACKMANN_JOIN_COLUMNS],
        on="canonical_match_key",
        how="left",
        validate="one_to_one",
    )

    accepted["match_method"] = MATCH_METHOD_MANUAL
    accepted["review_flag"] = False
    for column in _NA_DIAGNOSTIC_COLUMNS:
        accepted[column] = pd.NA

    return accepted[CROSSWALK_COLUMNS]
