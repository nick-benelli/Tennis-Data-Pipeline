"""Stage-2 raw checkpoint: persist Tennis-Data UK downloads to disk, unmodified.

A raw checkpoint is byte-for-byte the source's own columns - no renaming, no
dtype coercion. Re-running a download for a given year overwrites that year's
checkpoint file; nothing downstream depends on it being append-only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...config import settings
from .client import TennisDataUKClient, Tour

logger = logging.getLogger(__name__)

# The raw column that identifies the tour's own tournament id.
_TOUR_ID_COLUMN = {Tour.ATP: "ATP", Tour.WTA: "WTA"}


class RawCheckpointError(Exception):
    """Raised when a downloaded/checkpointed DataFrame doesn't look like the requested tour's data."""


def raw_checkpoint_path(
    tour: Tour | str, year: int, raw_dir: Path | None = None
) -> Path:
    """Path for one tour/season's Stage-2 raw checkpoint CSV.

    `raw_dir` defaults to `settings.paths.raw / tennis_data_uk.raw_dir_name`
    (config.yaml's `paths.raw_dir` / `tennis_data_uk.raw_dir_name`); the
    filename comes from `tennis_data_uk.raw_filename_template`.
    """
    tour = Tour(str(tour).lower())
    tennis_data_uk_settings = settings.tennis_data_uk

    raw_dir = (
        raw_dir
        if raw_dir is not None
        else settings.paths.raw / tennis_data_uk_settings.raw_dir_name
    )
    filename = tennis_data_uk_settings.raw_filename_template.format(
        tour=tour.value, year=year
    )
    return raw_dir / tour.value / filename


def _check_tour_column(df: pd.DataFrame, tour: Tour, year: int) -> None:
    """Guard against saving the wrong tour's data (seen for real: 2024 WTA raw file)."""
    expected = _TOUR_ID_COLUMN[tour]
    other_tour = Tour.WTA if tour == Tour.ATP else Tour.ATP
    other = _TOUR_ID_COLUMN[other_tour]

    if expected not in df.columns:
        if other in df.columns:
            raise RawCheckpointError(
                f"Refusing to checkpoint {tour.value.upper()} {year}: data has a "
                f"'{other}' column ({other_tour.value.upper()}'s id), not '{expected}'. "
                "This looks like the wrong tour's data."
            )
        raise RawCheckpointError(
            f"Refusing to checkpoint {tour.value.upper()} {year}: no '{expected}' "
            "column found in the downloaded data."
        )


def _warn_on_schema_drift(df: pd.DataFrame, path: Path) -> None:
    """Log a warning if the new download's columns differ from the previous checkpoint."""
    if not path.exists():
        return

    previous_columns = set(pd.read_csv(path, nrows=0).columns)
    new_columns = set(df.columns)

    added = new_columns - previous_columns
    removed = previous_columns - new_columns
    if added or removed:
        logger.warning(
            "Raw schema drift at %s: added=%s removed=%s",
            path,
            sorted(added),
            sorted(removed),
        )


def write_raw_checkpoint(
    df: pd.DataFrame,
    tour: Tour | str,
    year: int,
    raw_dir: Path | None = None,
) -> Path:
    """Persist a raw (untouched) season DataFrame, after sanity-checking it."""
    tour = Tour(str(tour).lower())
    _check_tour_column(df, tour, year)

    path = raw_checkpoint_path(tour, year, raw_dir)
    _warn_on_schema_drift(df, path)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def fetch_and_checkpoint(
    tour: Tour | str,
    year: int,
    *,
    client: TennisDataUKClient | None = None,
    raw_dir: Path | None = None,
) -> pd.DataFrame:
    """Download one season live and persist it as a Stage-2 raw checkpoint.

    This is the "how does the client grab the data and write the raw
    snapshot CSV" entry point - see `workflows.uk` for a
    higher-level, multi-year wrapper around this.
    """
    tour = Tour(str(tour).lower())
    client = client or TennisDataUKClient()

    df = client.load_year(year=year, tour=tour)
    write_raw_checkpoint(df, tour, year, raw_dir)
    return df
