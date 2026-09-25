"""Combine Pass 0, Pass 1, and Pass 2 into the full UK<->Sackmann match-linking pipeline."""

from __future__ import annotations

import pandas as pd

from .pass0 import build_manual_links
from .pass1 import _attach_sackmann, _attach_uk, add_sackmann_match_key, build_rank_links
from .pass2 import build_name_pair_links


def build_rank_and_name_links(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    tournament_mapper_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Pass 1 (`build_rank_links`) then Pass 2 (`build_name_pair_links`).

    Pass 2's UK input is every tournament-attached UK row whose
    `source_match_key` isn't in Pass 1's *accepted* links - i.e. "not already
    resolved by Pass 1", which includes both rows with no rank-pair candidate
    at all *and* rows that were part of a Pass-1 ambiguous group (a rank-pair
    ambiguity only means rank matching was insufficient; tournament + round +
    name-pair evidence may still resolve it uniquely). Pass 2's Sackmann
    input is every tournament-attached Sackmann row whose `canonical_match_key`
    isn't in Pass 1's accepted links, for the same reason.

    Returns `(accepted_links, ambiguous_candidates, unmatched_uk_rows)`: the
    two passes' accepted links concatenated (columns differ between passes,
    e.g. Pass 1 has raw `winner_rank`/`loser_rank`, Pass 2 has
    `winner_rank_agrees`/`loser_rank_agrees`/`data_quality_flag` - absent
    columns are NaN for the other pass's rows), their ambiguous candidates
    concatenated likewise, and Pass 2's final unmatched UK rows.

    Raises `AssertionError` if Pass 1 and Pass 2 ever accept overlapping
    `source_match_key`/`canonical_match_key` values.
    """
    accepted1, ambiguous1, _unmatched_uk = build_rank_links(uk_df, sackmann_df, tournament_mapper_df)

    uk_linked = _attach_uk(uk_df, tournament_mapper_df)
    uk_residual = uk_linked.loc[
        ~uk_linked["source_match_key"].isin(accepted1["source_match_key"])
    ].copy()

    sackmann_linked = _attach_sackmann(add_sackmann_match_key(sackmann_df), tournament_mapper_df)
    sackmann_residual = sackmann_linked.loc[
        ~sackmann_linked["canonical_match_key"].isin(accepted1["canonical_match_key"])
    ].copy()

    accepted2, ambiguous2, unmatched_uk_rows = build_name_pair_links(uk_residual, sackmann_residual)

    if set(accepted1["source_match_key"]) & set(accepted2["source_match_key"]) or set(
        accepted1["canonical_match_key"]
    ) & set(accepted2["canonical_match_key"]):
        raise AssertionError("Pass 1 and Pass 2 accepted links must not share match keys")

    accepted = pd.concat([accepted1, accepted2], ignore_index=True)
    ambiguous = pd.concat([ambiguous1, ambiguous2], ignore_index=True)

    return accepted, ambiguous, unmatched_uk_rows


def build_manual_rank_and_name_links(
    uk_df: pd.DataFrame,
    sackmann_df: pd.DataFrame,
    tournament_mapper_df: pd.DataFrame,
    manual_links_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run Pass 0 (`build_manual_links`) first, then Pass 1 + Pass 2 on what's left.

    Manual links are resolved and removed from both sides' pools *before*
    Pass 1/2 run, so a manually-confirmed pair can never be reconsidered - or
    wrongly reclaimed for a different match - by either algorithmic pass.
    Pass 1/2 themselves are unchanged (`build_rank_and_name_links`, run here
    on the post-Pass-0 residual).

    Returns `(accepted_links, ambiguous_candidates, unmatched_uk_rows)` in the
    same shape as `build_rank_and_name_links`, with Pass 0's accepted links
    concatenated in front (`match_method` == `MATCH_METHOD_MANUAL`).
    """
    accepted0 = build_manual_links(uk_df, sackmann_df, tournament_mapper_df, manual_links_df)

    uk_residual0 = uk_df.loc[~uk_df["source_match_key"].isin(accepted0["source_match_key"])].copy()
    sackmann_with_key = add_sackmann_match_key(sackmann_df)
    sackmann_residual0 = sackmann_with_key.loc[
        ~sackmann_with_key["canonical_match_key"].isin(accepted0["canonical_match_key"])
    ].copy()

    accepted12, ambiguous, unmatched_uk_rows = build_rank_and_name_links(
        uk_residual0, sackmann_residual0, tournament_mapper_df
    )

    accepted = pd.concat([accepted0, accepted12], ignore_index=True)

    return accepted, ambiguous, unmatched_uk_rows
