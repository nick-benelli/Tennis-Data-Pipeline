"""Attach `official_tournament_id` to a source's match rows."""

from __future__ import annotations

import pandas as pd


def attach_tournament_ids(
    matches: pd.DataFrame,
    tournament_mapper: pd.DataFrame,
    *,
    source: str,
    match_tournament_col: str,
    year_col: str,
) -> pd.DataFrame:
    """Attach `official_tournament_id` to a source's match rows.

    Looks up `tournament_mapper` rows where `source` equals `source`, keyed by
    (`year_col`, `match_tournament_col`) in `matches` against Sackmann's/`UK`s
    (`year`, `source_tournament_id`) in `tournament_mapper`. Every other column
    in `matches` is left unchanged - this only adds `official_tournament_id`.

    Raises a `pandas.errors.MergeError` (via `validate="many_to_one"`) if
    `tournament_mapper` has more than one `official_tournament_id` for the
    same (`year_col`, `match_tournament_col`) combination.
    """
    mapper = (
        tournament_mapper.loc[
            tournament_mapper["source"].eq(source),
            ["year", "source_tournament_id", "official_tournament_id"],
        ]
        .drop_duplicates()
        .rename(columns={"year": year_col, "source_tournament_id": match_tournament_col})
    )

    return matches.merge(
        mapper,
        on=[year_col, match_tournament_col],
        how="left",
        validate="many_to_one",
    )
