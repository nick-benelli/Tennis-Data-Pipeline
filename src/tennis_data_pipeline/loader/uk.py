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


def load_clean_uk_year(
    tour: str, year: int, project_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load a single season's cleaned UK ATP/WTA matches CSV by year.

    Directory/filename come from `tennis_data_uk.clean_dir_name`/
    `clean_filename_template` (config.yaml) under `settings.paths.clean` -
    the same config workflows.tennis_data_uk.clean_checkpoint_path() uses, so
    the two stay in sync. `project_dir` defaults to `settings.paths.project_dir`
    (override via the TENNIS_DATA_PIPELINE_PROJECT_DIR env var); pass it to
    load from a different project root's `paths.clean_dir`.
    """
    tennis_data_uk_settings = settings.tennis_data_uk
    clean_root = (
        Path(project_dir) / settings.paths.clean_dir
        if project_dir is not None
        else settings.paths.clean
    )
    clean_dir = clean_root / tennis_data_uk_settings.clean_dir_name
    filename = tennis_data_uk_settings.clean_filename_template.format(
        tour=tour, year=year
    )
    return load_clean_uk_data(clean_dir / tour / filename, tour)


def load_clean_uk_data_range(
    tour: str, years: range | list[int], project_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK ATP/WTA matches CSVs."""
    return pd.concat(
        [load_clean_uk_year(tour, year, project_dir) for year in years],
        ignore_index=True,
    )


def load_clean_uk_combined(
    years: range | list[int], project_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate ATP+WTA cleaned matches for the given years (same schema, both tours)."""
    return pd.concat(
        [
            load_clean_uk_data_range("atp", years, project_dir),
            load_clean_uk_data_range("wta", years, project_dir),
        ],
        ignore_index=True,
    )


# Backward-compatible ATP-only aliases.
def load_clean_uk_atp_data(path: Path | str) -> pd.DataFrame:
    """Load a single cleaned UK ATP matches CSV with dtypes restored."""
    return load_clean_uk_data(path, tour="atp")


def load_clean_uk_atp_year(
    year: int, project_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load a single season's cleaned UK ATP matches CSV by year."""
    return load_clean_uk_year("atp", year, project_dir)


def load_clean_uk_atp_data_range(
    years: range | list[int], project_dir: Path | str | None = None
) -> pd.DataFrame:
    """Load and concatenate several seasons' cleaned UK ATP matches CSVs."""
    return load_clean_uk_data_range("atp", years, project_dir)


__all__ = [
    "load_clean_uk_data",
    "load_clean_uk_year",
    "load_clean_uk_data_range",
    "load_clean_uk_combined",
    "load_clean_uk_atp_data",
    "load_clean_uk_atp_year",
    "load_clean_uk_atp_data_range",
]
