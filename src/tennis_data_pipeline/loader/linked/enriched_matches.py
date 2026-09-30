"""Load one tour+year's analysis-ready enriched UK matches CSV (`enriched_matches_path`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .. import uk as uk_loader
from .paths import enriched_matches_path, year_output_dir

# The linkage block's dtypes, appended by `mapper.matches.uk_sackmann.outputs.
# build_enriched_matches` on top of the UK source's own columns (already
# restored by `loader.uk.load_clean_uk_data`).
_INT_COLS = ["official_tournament_id", "canonical_winner_id", "canonical_loser_id"]
_BOOLEAN_COLS = ["review_flag"]
_CATEGORY_COLS = ["match_method", "canonical_round"]
_STRING_COLS = [
    "canonical_match_key",
    "canonical_tourney_id",
    "canonical_tourney_name",
    "canonical_winner_name",
    "canonical_loser_name",
    "data_quality_flag",
]


def load_enriched_matches(tour: str, year: int, linked_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour+year's analysis-ready enriched UK matches CSV with dtypes restored.

    Starts from `loader.uk.load_clean_uk_data` (every UK source column, which
    `build_enriched_matches` keeps as-is), then restores the appended
    linkage/canonical block's dtypes on top.
    """
    tour = str(tour).lower()
    output_dir = year_output_dir(tour, year, linked_dir)
    df = uk_loader.load_clean_uk_data(enriched_matches_path(output_dir, tour, year), tour)

    for col in _INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in _BOOLEAN_COLS:
        if col in df.columns:
            df[col] = df[col].astype("boolean")

    for col in _CATEGORY_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    for col in _STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


__all__ = ["load_enriched_matches"]
