"""Stage 3-4: clean a raw checkpoint into the canonical schema.

"turn a raw checkpoint into the clean, canonical-schema dataset"
(`clean_year`/`clean_years`). The known-fixes/validation/rename logic lives
in `handler.uk.cleaner.atp`/`handler.uk.cleaner.wta`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ...config import settings
from ...datasources.tennis_data_uk.checkpoint import raw_checkpoint_path
from ...datasources.tennis_data_uk.client import Tour
from ...handler.uk.cleaner import atp, quality, wta

logger = logging.getLogger(__name__)


def clean_checkpoint_path(tour: Tour | str, year: int, clean_dir: Path | None = None) -> Path:
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
    filename = tennis_data_uk_settings.clean_filename_template.format(tour=tour.value, year=year)
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
    clean_path, rows = _clean_and_write_year(tour, year, raw_dir=raw_dir, clean_dir=clean_dir)
    logger.info("[%s %s] Wrote %d rows to %s", tour.value.upper(), year, rows, clean_path)
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


__all__ = [
    "CleanYearResult",
    "clean_checkpoint_path",
    "clean_year",
    "clean_years",
    "log_clean_summary",
    "quality_report_path",
]
