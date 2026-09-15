"""Load cleaned Tennis-Data UK CSVs with their intended dtypes restored.

`clean_uk_atp_data` produces categoricals, nullable ints, and parsed dates, but
writing to CSV and reading it back with plain `pd.read_csv` loses all of that
(everything round-trips as generic object/int64/float64). This restores it.
"""

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.cleaner.uk import atp_cols as cols

CATEGORY_COLS = [
    "source",
    "tour",
    "series",
    "indoor_outdoor",
    "surface",
    "round",
    "match_status",
]

STRING_COLS = [
    "tournament_name",
    "location",
    "winner_name",
    "loser_name",
    "source_event_key",
    "source_match_key",
]

DATE_COLS = ["match_date"]

# Whole numbers that can be missing (e.g. retired matches leave later sets blank).
NULLABLE_INT_COLS = [
    "year",
    "uk_tournament_id",
    "best_of",
    "winner_rank",
    "loser_rank",
    "winner_rank_points",
    "loser_rank_points",
    "winner_sets",
    "loser_sets",
    "winner_set_1_games",
    "loser_set_1_games",
    "winner_set_2_games",
    "loser_set_2_games",
    "winner_set_3_games",
    "loser_set_3_games",
    "winner_set_4_games",
    "loser_set_4_games",
    "winner_set_5_games",
    "loser_set_5_games",
]


def load_clean_uk_atp_data(path: Path | str) -> pd.DataFrame:
    """Load a single cleaned UK ATP matches CSV with dtypes restored."""
    df = pd.read_csv(path, parse_dates=DATE_COLS)

    for col in NULLABLE_INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in cols.ODDS_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in CATEGORY_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


def load_clean_uk_atp_year(project_dir: Path, year: int) -> pd.DataFrame:
    """Load a single season's cleaned UK ATP matches CSV by year."""
    path = project_dir / f"data/clean/tennis-data-uk/atp/uk_atp_singles_matches_{year}.csv"
    return load_clean_uk_atp_data(path)


def load_clean_uk_atp_data_range(project_dir: Path, years: range | list[int]) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK ATP matches CSVs."""
    return pd.concat(
        [load_clean_uk_atp_year(project_dir, year) for year in years],
        ignore_index=True,
    )


__all__ = [
    "load_clean_uk_atp_data",
    "load_clean_uk_atp_year",
    "load_clean_uk_atp_data_range",
]