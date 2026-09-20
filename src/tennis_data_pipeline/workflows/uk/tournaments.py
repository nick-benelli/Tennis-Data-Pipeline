"""Stage 5: derive and persist the tournament-summary table from clean checkpoints."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...config import settings
from ...datasources.tennis_data_uk.client import Tour
from ...handler.uk.cleaner.tournaments import (
    CLEAN_TOURNAMENT_KEY_COLUMNS,
    build_uk_tournament_table,
)
from ...loader.uk import load_clean_uk_data
from .clean import clean_checkpoint_path

logger = logging.getLogger(__name__)


def tournament_table_path(tour: Tour | str, clean_dir: Path | None = None) -> Path:
    """Path for one tour's shared tournament-summary CSV (see `build_uk_tournament_table`)."""
    tour = Tour(str(tour).lower())
    tennis_data_uk_settings = settings.tennis_data_uk

    clean_dir = (
        clean_dir
        if clean_dir is not None
        else settings.paths.clean / tennis_data_uk_settings.clean_dir_name
    )
    filename = tennis_data_uk_settings.tournament_filename_template.format(
        tour=tour.value
    )
    return clean_dir / tour.value / tennis_data_uk_settings.tournament_dir_name / filename


def tournament_inconsistencies_path(
    tour: Tour | str, clean_dir: Path | None = None
) -> Path:
    """Path for one tour's tournament-attribute-inconsistencies CSV (never silently dropped)."""
    tour = Tour(str(tour).lower())
    tennis_data_uk_settings = settings.tennis_data_uk

    clean_dir = (
        clean_dir
        if clean_dir is not None
        else settings.paths.clean / tennis_data_uk_settings.clean_dir_name
    )
    filename = tennis_data_uk_settings.tournament_inconsistencies_filename_template.format(
        tour=tour.value
    )
    return clean_dir / tour.value / tennis_data_uk_settings.tournament_dir_name / filename


def _upsert_csv(
    path: Path,
    rows: pd.DataFrame,
    *,
    key_columns: list[str],
    date_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Merge `rows` into the CSV at `path`, keyed on `key_columns` (new rows win on conflict)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = pd.read_csv(path, parse_dates=date_columns or [])
        combined = pd.concat([existing, rows], ignore_index=True)
    else:
        combined = rows

    combined = combined.drop_duplicates(subset=key_columns, keep="last")

    # A "num_*" column absent from one side of the concat (e.g. a match status
    # that only shows up in some runs) means "none seen", not "unknown".
    count_cols = [c for c in combined.columns if c.startswith("num_")]
    combined[count_cols] = combined[count_cols].fillna(0)

    combined = combined.sort_values(key_columns).reset_index(drop=True)
    combined.to_csv(path, index=False)
    return combined


def build_uk_tournaments(
    tour: Tour | str,
    years: range | list[int],
    *,
    clean_dir: Path | None = None,
) -> tuple[Path, int, int]:
    """Build/update one tour's tournament-summary table from its Stage-4 clean checkpoints.

    Loads each requested season's already-cleaned checkpoint (skipping, with a
    warning, any year that hasn't been cleaned yet via `clean_year`/`clean_years`),
    derives one row per tournament
    (`handler.uk.cleaner.tournaments.build_uk_tournament_table`), and upserts the
    result into the tour's shared tournaments CSV - keyed on
    tour/year/uk_tournament_id/location, so re-running a subset of years only
    touches those years' rows. Tournaments whose attributes aren't consistent
    across their matches are upserted into a companion inconsistencies CSV
    instead of being silently dropped.

    Returns (`table_path`, tournament rows now in the file, inconsistency rows
    found this run).

    Raises:
        FileNotFoundError: If none of the requested years have a clean checkpoint.

    """
    tour = Tour(str(tour).lower())

    frames = []
    for year in years:
        path = clean_checkpoint_path(tour, year, clean_dir)
        if not path.exists():
            logger.warning(
                "[%s %s] No clean checkpoint at %s, skipping",
                tour.value.upper(),
                year,
                path,
            )
            continue
        frames.append(load_clean_uk_data(path, tour.value))

    if not frames:
        raise FileNotFoundError(
            f"No clean checkpoints found for {tour.value.upper()} in years {list(years)}"
        )

    df = pd.concat(frames, ignore_index=True)
    result = build_uk_tournament_table(df)

    table_path = tournament_table_path(tour, clean_dir)
    combined = _upsert_csv(
        table_path,
        result.tournaments,
        key_columns=CLEAN_TOURNAMENT_KEY_COLUMNS,
        date_columns=["start_date", "end_date"],
    )
    logger.info(
        "[%s] Wrote %d tournament(s) to %s", tour.value.upper(), len(combined), table_path
    )

    if not result.inconsistencies.empty:
        inconsistencies_path = tournament_inconsistencies_path(tour, clean_dir)
        _upsert_csv(
            inconsistencies_path,
            result.inconsistencies.reset_index(),
            key_columns=CLEAN_TOURNAMENT_KEY_COLUMNS,
        )
        logger.warning(
            "[%s] %d tournament(s) have inconsistent attributes - see %s",
            tour.value.upper(),
            len(result.inconsistencies),
            inconsistencies_path,
        )

    return table_path, len(combined), len(result.inconsistencies)


__all__ = [
    "build_uk_tournaments",
    "tournament_inconsistencies_path",
    "tournament_table_path",
]
