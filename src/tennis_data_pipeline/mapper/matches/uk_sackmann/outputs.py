"""Build the formalized, per-year UK<->Sackmann linkage output tables.

Pure `DataFrame`-in/`DataFrame`-out functions - no file I/O here (see
`workflows.mapper.matches.uk_sackmann` for that layer). Consumes the
`(accepted, ambiguous, unmatched)` tuple `build_rank_and_name_links` returns
and reshapes it into four purpose-built tables:

- `build_match_crosswalk`: compact lineage crosswalk (IDs + diagnostics only).
- `build_enriched_matches`: the full UK dataset + a handful of linkage/
  canonical columns, for downstream analysis - every UK row is kept.
- `finalize_link_status`: resolves rows Pass 2 reconsidered (and either
  accepted or left still-ambiguous) so `ambiguous`/`unmatched` reflect the
  pipeline's *final* state with no row double-counted across buckets.
- `build_linkage_summary`: one coverage/health row for the (tour, year).
"""

from __future__ import annotations

import pandas as pd

from .pass1 import add_sackmann_match_key
from .schema import (
    MATCH_METHOD_MANUAL,
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
)

MATCH_CROSSWALK_COLUMNS = [
    "year",
    "tour",
    "source_match_key",
    "canonical_match_key",
    "official_tournament_id",
    "winner_id",
    "loser_id",
    "match_method",
    "review_flag",
    "data_quality_flag",
    "source_candidate_count",
    "canonical_candidate_count",
    "round_agrees",
    "winner_rank_points_diff",
    "loser_rank_points_diff",
]

# Linkage columns copied onto every UK row in the enriched dataset (from `accepted`).
_ENRICHMENT_LINK_COLUMNS = [
    "source_match_key",
    "canonical_match_key",
    "official_tournament_id",
    "winner_id",
    "loser_id",
    "match_method",
    "review_flag",
    "data_quality_flag",
]

# `accepted`'s winner_id/loser_id are already Sackmann's - renamed on the way in
# so they're never mistaken for the UK source's own winner_name/loser_name-keyed
# identity once both sit side by side on the same enriched row.
_ENRICHMENT_LINK_RENAME = {"winner_id": "canonical_winner_id", "loser_id": "canonical_loser_id"}

# A small number of canonical (Sackmann) fields copied onto matched rows, renamed
# with a `canonical_` prefix so they're never confused with the UK source columns.
_CANONICAL_ENRICHMENT_COLUMNS = {
    "winner_name": "canonical_winner_name",
    "loser_name": "canonical_loser_name",
    "tourney_id": "canonical_tourney_id",
    "tourney_name": "canonical_tourney_name",
    "round": "canonical_round",
}

# Fixed order for the block appended after every native UK column: canonical
# identity -> tournament -> players -> linkage metadata last (easiest to scan).
ENRICHED_LINKAGE_BLOCK_COLUMNS = [
    "canonical_match_key",
    "official_tournament_id",
    "canonical_tourney_id",
    "canonical_tourney_name",
    "canonical_round",
    "canonical_winner_id",
    "canonical_winner_name",
    "canonical_loser_id",
    "canonical_loser_name",
    "match_method",
    "review_flag",
    "data_quality_flag",
]

LINKAGE_SUMMARY_COLUMNS = [
    "year",
    "tour",
    "uk_total_matches",
    "sackmann_total_matches",
    "linked_matches",
    "linked_manual",
    "linked_pass_1",
    "linked_pass_2",
    "ambiguous_matches",
    "unmatched_matches",
    "coverage_pct",
    # Populated by the workflow layer (see workflows.mapper.matches.uk_sackmann.
    # build_match_links) - left NA here since build_linkage_summary is a pure,
    # deterministic function and reading the clock isn't its job.
    "linked_at",
]


def build_match_crosswalk(accepted: pd.DataFrame) -> pd.DataFrame:
    """Build the compact lineage crosswalk: one row per accepted link.

    Not every column in `MATCH_CROSSWALK_COLUMNS` exists on every accepted
    row - Pass 1 has no `data_quality_flag`/Pass 2 has no
    `winner_rank_points_diff`, for example - missing ones are filled with NA.

    Raises `ValueError` if `source_match_key` or `canonical_match_key` isn't
    unique in `accepted`.
    """
    if accepted["source_match_key"].duplicated().any():
        raise ValueError("accepted['source_match_key'] must be unique")
    if accepted["canonical_match_key"].duplicated().any():
        raise ValueError("accepted['canonical_match_key'] must be unique")

    return accepted.reindex(columns=MATCH_CROSSWALK_COLUMNS).reset_index(drop=True)


def _validate_winner_loser_ids(accepted: pd.DataFrame, sackmann_df: pd.DataFrame) -> None:
    """Raise `AssertionError` if any accepted row's winner_id/loser_id disagrees with
    the Sackmann row its `canonical_match_key` actually points to."""
    canonical_ids = sackmann_df.reindex(columns=["canonical_match_key", "winner_id", "loser_id"]).rename(
        columns={"winner_id": "_canonical_winner_id", "loser_id": "_canonical_loser_id"}
    )
    checked = accepted.reindex(columns=["canonical_match_key", "winner_id", "loser_id"]).merge(
        canonical_ids, on="canonical_match_key", how="left"
    )
    mismatched = checked.loc[
        (checked["winner_id"] != checked["_canonical_winner_id"])
        | (checked["loser_id"] != checked["_canonical_loser_id"])
    ]
    if not mismatched.empty:
        raise AssertionError(
            "accepted winner_id/loser_id must match the linked canonical_match_key's "
            f"Sackmann row - mismatched keys: {mismatched['canonical_match_key'].tolist()}"
        )


def build_enriched_matches(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    accepted: pd.DataFrame,
) -> pd.DataFrame:
    """Enrich every UK match row with its canonical link, if any.

    Starts from *all* of `uk_df` - unmatched rows are kept, with null
    linkage/canonical columns - and appends a small, fixed set of linkage and
    canonical columns. This is not a full merge against the entire Sackmann
    schema.

    Raises `ValueError` if `uk_df`, `accepted`, or `sackmann_df` don't have
    unique `source_match_key`/`canonical_match_key` as appropriate.
    Raises `AssertionError` if the result's row count doesn't match `uk_df`'s,
    or if any accepted row's `winner_id`/`loser_id` doesn't match the
    `canonical_match_key` it's linked to (a should-never-happen construction
    guard, not a real-world data-quality check).
    """
    if uk_df["source_match_key"].duplicated().any():
        raise ValueError("uk_df['source_match_key'] must be unique")
    if accepted["source_match_key"].duplicated().any():
        raise ValueError("accepted['source_match_key'] must be unique")
    if accepted["canonical_match_key"].duplicated().any():
        raise ValueError("accepted['canonical_match_key'] must be unique")

    if "canonical_match_key" not in sackmann_df.columns:
        sackmann_df = add_sackmann_match_key(sackmann_df)
    if sackmann_df["canonical_match_key"].duplicated().any():
        raise ValueError("sackmann_df's canonical_match_key must be unique")

    _validate_winner_loser_ids(accepted, sackmann_df)

    link_columns = accepted.reindex(columns=_ENRICHMENT_LINK_COLUMNS).rename(
        columns=_ENRICHMENT_LINK_RENAME
    )
    enriched = uk_df.merge(link_columns, on="source_match_key", how="left", validate="one_to_one")

    canonical_columns = sackmann_df.reindex(
        columns=["canonical_match_key", *_CANONICAL_ENRICHMENT_COLUMNS]
    ).rename(columns=_CANONICAL_ENRICHMENT_COLUMNS)
    enriched = enriched.merge(
        canonical_columns, on="canonical_match_key", how="left", validate="many_to_one"
    )

    if len(enriched) != len(uk_df):
        raise AssertionError("build_enriched_matches must preserve the source row count")

    # Full source row first, then the linkage block in a fixed, scannable order -
    # regardless of the merge order used to build it above.
    return enriched[[*uk_df.columns, *ENRICHED_LINKAGE_BLOCK_COLUMNS]]


def finalize_link_status(
    accepted: pd.DataFrame,
    ambiguous: pd.DataFrame,
    unmatched: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Resolve overlapping `source_match_key`s across passes to one final bucket each.

    `build_rank_and_name_links` reconsiders Pass-1-ambiguous rows in Pass 2,
    so the same `source_match_key` can appear in `ambiguous` (from Pass 1)
    *and* end up accepted, or still ambiguous, by Pass 2 - and a row can
    likewise appear in `ambiguous` while also having no Pass-2 candidate at
    all (landing in `unmatched` too). Precedence: linked > ambiguous >
    unmatched. Candidate rows for a key that stays ambiguous are preserved
    as-is (never collapsed to one row) - only keys resolved by a later pass
    are dropped.

    Returns `(ambiguous_final, unmatched_final)`; `accepted` is already final.
    """
    linked_keys = set(accepted["source_match_key"])
    ambiguous_final = ambiguous.loc[~ambiguous["source_match_key"].isin(linked_keys)].copy()

    resolved_keys = linked_keys | set(ambiguous_final["source_match_key"])
    unmatched_final = unmatched.loc[~unmatched["source_match_key"].isin(resolved_keys)].copy()

    return ambiguous_final, unmatched_final


def _unmatched_reason(unmatched: pd.DataFrame) -> pd.Series:
    """ "missing_tournament_mapping"/"no_rank_candidate"/"no_name_pair_candidate", derived
    purely from columns Pass 1/2 already attach - no new matching logic."""
    missing_tournament = unmatched["official_tournament_id"].isna()
    missing_rank = unmatched[["winner_rank", "loser_rank"]].isna().any(axis=1)

    reason = pd.Series("no_name_pair_candidate", index=unmatched.index, dtype="object")
    reason = reason.mask(missing_rank, "no_rank_candidate")
    reason = reason.mask(missing_tournament, "missing_tournament_mapping")
    return reason


def add_unmatched_diagnostics(unmatched: pd.DataFrame) -> pd.DataFrame:
    """Attach `linkage_status`/`unmatched_reason` review columns to the final unmatched table.

    `unmatched` must already be final (see `finalize_link_status`).
    `unmatched_reason` is best-effort - a coarse diagnosis from already-
    computed columns, not a substitute for eyeballing the row.
    """
    unmatched = unmatched.copy()
    unmatched["linkage_status"] = "unmatched"
    unmatched["unmatched_reason"] = _unmatched_reason(unmatched)
    return unmatched


def build_linkage_summary(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    accepted: pd.DataFrame,
    ambiguous: pd.DataFrame,
    unmatched: pd.DataFrame,
    *,
    year: int,
    tour: str,
) -> pd.DataFrame:
    """Build one summary row of coverage/health metrics for (`tour`, `year`).

    `ambiguous`/`unmatched` must already be final (see `finalize_link_status`)
    - counts are by unique `source_match_key`, never raw candidate rows.
    `sackmann_total_matches` is informational only (not part of the
    reconciliation check below, which is always against the UK side).
    `linked_at` is left NA - populated by the workflow layer, which is where
    "when did this run" belongs.

    Raises `AssertionError` if `linked + ambiguous + unmatched != uk_total_matches`.
    """
    total = uk_df["source_match_key"].nunique()
    linked = accepted["source_match_key"].nunique()
    ambiguous_count = ambiguous["source_match_key"].nunique()
    unmatched_count = unmatched["source_match_key"].nunique()

    if linked + ambiguous_count + unmatched_count != total:
        raise AssertionError(
            f"linked ({linked}) + ambiguous ({ambiguous_count}) + unmatched "
            f"({unmatched_count}) != uk_total_matches ({total})"
        )

    if "canonical_match_key" not in sackmann_df.columns:
        sackmann_df = add_sackmann_match_key(sackmann_df)
    sackmann_total = sackmann_df["canonical_match_key"].nunique()

    method_counts = accepted["match_method"].value_counts()

    return pd.DataFrame(
        [
            {
                "year": year,
                "tour": str(tour).lower(),
                "uk_total_matches": total,
                "sackmann_total_matches": sackmann_total,
                "linked_matches": linked,
                "linked_manual": int(method_counts.get(MATCH_METHOD_MANUAL, 0)),
                "linked_pass_1": int(method_counts.get(MATCH_METHOD_TOURNAMENT_RANK_UNIQUE, 0)),
                "linked_pass_2": int(method_counts.get(MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR, 0)),
                "ambiguous_matches": ambiguous_count,
                "unmatched_matches": unmatched_count,
                "coverage_pct": round(100 * linked / total, 1) if total else 0.0,
            }
        ],
        columns=LINKAGE_SUMMARY_COLUMNS,
    )
