"""High-level Tennis-Data UK workflows: download/checkpoint (Stage 1-2) and clean (Stage 3-4).

This is the easy, one-call entry point for both halves of the pipeline:

- "go grab the data from tennis-data.co.uk and write the raw snapshot CSV"
  (`fetch_and_checkpoint_year`/`fetch_and_checkpoint_years`). The actual
  download lives in `datasources.tennis_data_uk.client.TennisDataUKClient`;
  the actual checkpoint-writing (with the tour/schema-drift sanity checks)
  lives in `datasources.tennis_data_uk.checkpoint`.
- "load a raw checkpoint back for inspection, no cleaning" (`load_raw_year`).
- "turn a raw checkpoint into the clean, canonical-schema dataset"
  (`clean_year`/`clean_years`). The known-fixes/validation/rename logic lives
  in `handler.uk.cleaner.atp`/`handler.uk.cleaner.wta`.

This module just wires those pieces together with sensible, config-driven
defaults so callers don't need to think about paths:

    from tennis_data_pipeline.workflows.tennis_data_uk import (
        fetch_and_checkpoint_years,
        clean_years,
        log_clean_summary,
    )

    fetch_and_checkpoint_years("atp", range(2020, 2025))
    results = clean_years("atp", range(2020, 2025))
    log_clean_summary("atp", results)

Paths default to `settings.paths.raw` / `settings.paths.clean`, each joined
with `tennis_data_uk.raw_dir_name` / `tennis_data_uk.clean_dir_name`
(configure via config.yaml, or the TENNIS_DATA_PIPELINE_RAW_DIR /
TENNIS_DATA_PIPELINE_CLEAN_DIR env vars).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..config import settings
from ..datasources.tennis_data_uk.checkpoint import (
    fetch_and_checkpoint,
    raw_checkpoint_path,
)
from ..datasources.tennis_data_uk.client import TennisDataUKClient, Tour
from ..handler.uk.cleaner import atp, quality, wta
from ..handler.uk.cleaner.tournaments import (
    CLEAN_TOURNAMENT_KEY_COLUMNS,
    build_uk_tournament_table,
)
from ..loader.uk import load_clean_uk_data

logger = logging.getLogger(__name__)


def fetch_and_checkpoint_year(
    tour: Tour | str,
    year: int,
    *,
    client: TennisDataUKClient | None = None,
    raw_dir: Path | None = None,
) -> Path:
    """Download one tour/season live and persist it as a Stage-2 raw checkpoint.

    Returns the path the checkpoint CSV was written to.
    """
    tour = Tour(str(tour).lower())
    client = client or TennisDataUKClient()

    df = fetch_and_checkpoint(tour, year, client=client, raw_dir=raw_dir)

    path = raw_checkpoint_path(tour, year, raw_dir)
    logger.info("[%s %s] Wrote %d rows to %s", tour.value.upper(), year, len(df), path)
    return path


def fetch_and_checkpoint_years(
    tour: Tour | str,
    years: range | list[int],
    *,
    client: TennisDataUKClient | None = None,
    raw_dir: Path | None = None,
    fail_fast: bool = False,
) -> list[Path]:
    """Download and checkpoint several seasons for one tour.

    A bad/missing season is logged and skipped rather than aborting the whole
    batch, unless `fail_fast` is set.
    """
    tour = Tour(str(tour).lower())
    client = client or TennisDataUKClient()

    written: list[Path] = []
    for year in years:
        try:
            written.append(
                fetch_and_checkpoint_year(tour, year, client=client, raw_dir=raw_dir)
            )
        except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.exception(
                "[%s %s] Failed to fetch/checkpoint", tour.value.upper(), year
            )
            if fail_fast:
                raise

    return written


def load_raw_year(
    tour: Tour | str,
    year: int,
    *,
    raw_dir: Path | None = None,
) -> pd.DataFrame:
    """Load one season's Stage-2 raw checkpoint as-is, with proper dtypes but no cleaning.

    For inspecting/exploring the raw data (e.g. in a notebook). To get the
    fully cleaned dataset instead, use `clean_year`.
    """
    tour = Tour(str(tour).lower())
    path = raw_checkpoint_path(tour, year, raw_dir)

    if tour is Tour.ATP:
        return atp.load_raw_atp_csv(path, year)
    return wta.load_raw_wta_csv(path, year)


# --------------------------------------------------------------------------- #
# Stage 3-4: clean checkpoint
# --------------------------------------------------------------------------- #


def clean_checkpoint_path(
    tour: Tour | str, year: int, clean_dir: Path | None = None
) -> Path:
    """Path for one tour/season's Stage-4 clean checkpoint CSV.

    `clean_dir` defaults to `settings.paths.clean / tennis_data_uk.clean_dir_name`;
    the filename comes from `tennis_data_uk.clean_filename_template`.
    """
    tour = Tour(str(tour).lower())
    tennis_data_uk_settings = settings.tennis_data_uk

    clean_dir = (
        clean_dir
        if clean_dir is not None
        else settings.paths.clean / tennis_data_uk_settings.clean_dir_name
    )
    filename = tennis_data_uk_settings.clean_filename_template.format(
        tour=tour.value, year=year
    )
    return clean_dir / tour.value / filename


def quality_report_path(clean_dir: Path | None = None) -> Path:
    """Path for the shared ATP+WTA data-quality report CSV."""
    tennis_data_uk_settings = settings.tennis_data_uk
    clean_dir = (
        clean_dir
        if clean_dir is not None
        else settings.paths.clean / tennis_data_uk_settings.clean_dir_name
    )
    return clean_dir / tennis_data_uk_settings.quality_report_relpath


def _clean_and_write_year(
    tour: Tour,
    year: int,
    *,
    raw_dir: Path | None,
    clean_dir: Path | None,
) -> tuple[Path, int]:
    raw_path = raw_checkpoint_path(tour, year, raw_dir)
    clean_path = clean_checkpoint_path(tour, year, clean_dir)

    if tour is Tour.ATP:
        df_raw = atp.load_raw_atp_csv(raw_path, year)
        df_clean = atp.clean_atp_season(df_raw, year)
        report = atp.build_uk_atp_quality_report(df_clean)
    else:
        df_raw = wta.load_raw_wta_csv(raw_path, year)
        df_clean = wta.clean_wta_season(df_raw, year)
        report = wta.build_uk_wta_quality_report(df_clean)

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(clean_path, index=False)
    quality.update_quality_report(quality_report_path(clean_dir), report)

    return clean_path, len(df_clean)


def clean_year(
    tour: Tour | str,
    year: int,
    *,
    raw_dir: Path | None = None,
    clean_dir: Path | None = None,
) -> Path:
    """Load one season's Stage-2 raw checkpoint, run it through the known-fixes +
    validation + clean pipeline, and persist the Stage-4 clean checkpoint
    (updating the shared ATP+WTA quality report along the way).

    Returns the path the clean CSV was written to.
    """
    tour = Tour(str(tour).lower())
    clean_path, rows = _clean_and_write_year(
        tour, year, raw_dir=raw_dir, clean_dir=clean_dir
    )
    logger.info(
        "[%s %s] Wrote %d rows to %s", tour.value.upper(), year, rows, clean_path
    )
    return clean_path


@dataclass
class CleanYearResult:
    """Per-year outcome from `clean_years`, for building a batch summary."""

    year: int
    success: bool
    rows: int = 0
    error: str | None = None


def clean_years(
    tour: Tour | str,
    years: range | list[int],
    *,
    raw_dir: Path | None = None,
    clean_dir: Path | None = None,
    fail_fast: bool = False,
) -> list[CleanYearResult]:
    """Clean several seasons for one tour from their Stage-2 raw checkpoints.

    A bad/invalid season is logged and recorded as failed rather than
    aborting the whole batch, unless `fail_fast` is set.
    """
    tour = Tour(str(tour).lower())

    results: list[CleanYearResult] = []
    for year in years:
        try:
            clean_path, rows = _clean_and_write_year(
                tour,
                year,
                raw_dir=raw_dir,
                clean_dir=clean_dir,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.error("[%s %s] FAILED: %s", tour.value.upper(), year, exc)
            results.append(CleanYearResult(year=year, success=False, error=str(exc)))
            if fail_fast:
                raise
        else:
            logger.info(
                "[%s %s] Wrote %d rows to %s",
                tour.value.upper(),
                year,
                rows,
                clean_path,
            )
            results.append(CleanYearResult(year=year, success=True, rows=rows))

    return results


def log_clean_summary(tour: Tour | str, results: list[CleanYearResult]) -> None:
    """Log a per-year OK/FAILED table plus an overall success count."""
    tour = Tour(str(tour).lower())
    logger.info("=" * 60)
    logger.info("Summary (%s)", tour.value.upper())
    logger.info("=" * 60)
    for result in results:
        if result.success:
            logger.info("  %s: OK (%d rows)", result.year, result.rows)
        else:
            logger.info("  %s: FAILED - %s", result.year, result.error)

    succeeded = sum(result.success for result in results)
    logger.info("%d/%d year(s) succeeded.", succeeded, len(results))


# --------------------------------------------------------------------------- #
# Stage 5: tournament-summary table
# --------------------------------------------------------------------------- #


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
    "CleanYearResult",
    "build_uk_tournaments",
    "clean_checkpoint_path",
    "clean_year",
    "clean_years",
    "fetch_and_checkpoint_year",
    "fetch_and_checkpoint_years",
    "load_raw_year",
    "log_clean_summary",
    "quality_report_path",
    "tournament_inconsistencies_path",
    "tournament_table_path",
]
