"""Load cleaned Tennis-Data UK CSVs with their intended dtypes restored.

`clean_uk_atp_data`/`clean_uk_wta_data` produce categoricals, nullable ints,
and parsed dates, but writing to CSV and reading it back with plain
`pd.read_csv` loses all of that (everything round-trips as generic
object/int64/float64). This restores it.
"""

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.handler.uk.cleaner import common

CATEGORY_COLS = [
    "source",
    "tour",
    "series",
    "surface",
    "round",
    "match_status",
]

BOOLEAN_COLS = ["is_outdoor"]

STRING_COLS = [
    "tournament_name",
    "location",
    "winner_name",
    "loser_name",
    "source_event_key",
    "source_match_key",
]

DATE_COLS = ["match_date"]

# Whole numbers that can be missing (e.g. retired matches leave later sets blank,
# and WTA's set_4/set_5 are always missing since WTA singles is always best-of-3).
BASE_NULLABLE_INT_COLS = [
    "year",
    "uk_tournament_id",
    "best_of",
    "winner_rank",
    "loser_rank",
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

# rank_points is nullable-int for ATP, but WTA's 2007 season has fractional
# values (a since-changed ranking-points formula), so it's kept as float there.
RANK_POINTS_COLS = ["winner_rank_points", "loser_rank_points"]


def load_clean_uk_data(path: Path | str, tour: str) -> pd.DataFrame:
    """Load a single cleaned UK ATP/WTA matches CSV with dtypes restored."""
    df = pd.read_csv(path, parse_dates=DATE_COLS)

    nullable_int_cols = list(BASE_NULLABLE_INT_COLS)
    if tour == "atp":
        nullable_int_cols += RANK_POINTS_COLS

    for col in nullable_int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if tour == "wta":
        for col in RANK_POINTS_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in common.ODDS_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in CATEGORY_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    for col in BOOLEAN_COLS:
        if col in df.columns:
            df[col] = df[col].astype("boolean")

    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].astype("string")

    return df


def _default_clean_dir() -> Path:
    """`settings.paths.clean / tennis_data_uk.clean_dir_name` - same default
    `workflows.uk.clean.clean_checkpoint_path` uses, so callers stay in sync
    without passing `clean_dir` explicitly.
    """
    return settings.paths.clean / settings.tennis_data_uk.clean_dir_name


def load_clean_uk_year(tour: str, year: int, clean_dir: Path | str | None = None) -> pd.DataFrame:
    """Load a single season's cleaned UK ATP/WTA matches CSV by year.

    `clean_dir` defaults to `_default_clean_dir()` (i.e. `settings.paths.clean`,
    which honors `TENNIS_DATA_PIPELINE_CLEAN_DIR`/`TENNIS_DATA_PIPELINE_PROJECT_DIR`);
    pass it to load from a different clean-data root instead.
    """
    clean_dir = Path(clean_dir) if clean_dir is not None else _default_clean_dir()
    filename = settings.tennis_data_uk.clean_filename_template.format(tour=tour, year=year)
    return load_clean_uk_data(clean_dir / tour / filename, tour)


def load_clean_uk_data_range(
    tour: str, years: range | list[int], clean_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK ATP/WTA matches CSVs."""
    return pd.concat(
        [load_clean_uk_year(tour, year, clean_dir) for year in years],
        ignore_index=True,
    )


def load_clean_uk_combined(
    years: range | list[int], clean_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate ATP+WTA cleaned matches for the given years (same schema, both tours)."""
    return pd.concat(
        [
            load_clean_uk_data_range("atp", years, clean_dir),
            load_clean_uk_data_range("wta", years, clean_dir),
        ],
        ignore_index=True,
    )


# -------- ATP-only aliases --------


# Backward-compatible ATP-only aliases.
def load_clean_uk_atp_data(path: Path | str) -> pd.DataFrame:
    """Load a single cleaned UK ATP matches CSV with dtypes restored."""
    return load_clean_uk_data(path, tour="atp")


def load_clean_uk_atp_year(year: int, clean_dir: Path | str | None = None) -> pd.DataFrame:
    """Load a single season's cleaned UK ATP matches CSV by year."""
    return load_clean_uk_year("atp", year, clean_dir)


def load_clean_uk_atp_data_range(
    years: range | list[int], clean_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK ATP matches CSVs."""
    return load_clean_uk_data_range("atp", years, clean_dir)


# -------- WTA-only aliases --------


# WTA-only aliases (same shape as the ATP ones above).
def load_clean_uk_wta_data(path: Path | str) -> pd.DataFrame:
    """Load a single cleaned UK WTA matches CSV with dtypes restored."""
    return load_clean_uk_data(path, tour="wta")


def load_clean_uk_wta_year(year: int, clean_dir: Path | str | None = None) -> pd.DataFrame:
    """Load a single season's cleaned UK WTA matches CSV by year."""
    return load_clean_uk_year("wta", year, clean_dir)


def load_clean_uk_wta_data_range(
    years: range | list[int], clean_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK WTA matches CSVs."""
    return load_clean_uk_data_range("wta", years, clean_dir)


__all__ = [
    "load_clean_uk_data",
    "load_clean_uk_year",
    "load_clean_uk_data_range",
    "load_clean_uk_combined",
    "load_clean_uk_atp_data",
    "load_clean_uk_atp_year",
    "load_clean_uk_atp_data_range",
    "load_clean_uk_wta_data",
    "load_clean_uk_wta_year",
    "load_clean_uk_wta_data_range",
]
