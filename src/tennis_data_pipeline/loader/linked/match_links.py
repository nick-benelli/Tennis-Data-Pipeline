"""Load one tour+year's compact lineage crosswalk CSV (`match_crosswalk_path`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .paths import match_crosswalk_path, year_output_dir

# MATCH_CROSSWALK_COLUMNS' dtypes, split like loader.uk/loader.mapper: nullable
# ints for anything that can be missing (Pass 1 has no data_quality_flag, Pass 2
# has no winner_rank_points_diff), nullable booleans for the two flag columns,
# and plain "string" for identity/method columns.
_INT_COLS = [
    "year",
    "official_tournament_id",
    "winner_id",
    "loser_id",
    "source_candidate_count",
    "canonical_candidate_count",
]
_FLOAT_COLS = ["winner_rank_points_diff", "loser_rank_points_diff"]
_BOOLEAN_COLS = ["review_flag", "round_agrees"]
_CATEGORY_COLS = ["tour", "match_method"]
_STRING_COLS = [
    "source_match_key",
    "canonical_match_key",
    "data_quality_flag",
]


def load_match_links(tour: str, year: int, linked_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour+year's compact lineage crosswalk CSV with dtypes restored."""
    tour = str(tour).lower()
    output_dir = year_output_dir(tour, year, linked_dir)
    df = pd.read_csv(match_crosswalk_path(output_dir, tour, year))

    for col in _INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in _FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")

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


__all__ = ["load_match_links"]
