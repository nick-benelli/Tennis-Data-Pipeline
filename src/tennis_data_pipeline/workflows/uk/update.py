"""Stage 6: scheduled/weekly update (fetch + clean + tournaments).

Best-effort per tour/year so it's safe to run unattended (e.g. a weekly GitHub Action).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ...datasources.tennis_data_uk.checkpoint import raw_checkpoint_path
from ...datasources.tennis_data_uk.client import (
    TennisDataUKClient,
    TennisDataUKDownloadError,
    Tour,
)
from .clean import _clean_and_write_year
from .fetch import fetch_and_checkpoint_year
from .tournaments import build_uk_tournaments

logger = logging.getLogger(__name__)


@dataclass
class YearUpdateResult:
    """Per (tour, year) outcome from `update_current_season`."""

    tour: str
    year: int
    fetched: bool = False
    fetch_error: str | None = None
    # True for anything other than a plain download failure (site down/404) -
    # e.g. a RawCheckpointError, which means the downloaded data looks wrong.
    fetch_needs_attention: bool = False
    cleaned: bool = False
    clean_error: str | None = None
    rows: int = 0


@dataclass
class SeasonUpdateReport:
    """Overall outcome from `update_current_season`; scripts/CI act on `needs_attention`."""

    results: list[YearUpdateResult]
    tournament_tables: dict[str, Path] = field(default_factory=dict)
    tournament_errors: dict[str, str] = field(default_factory=dict)

    @property
    def needs_attention(self) -> bool:
        """True if anything here needs a human (a new known-fix, or an unexpected failure).

        Deliberately excludes plain fetch failures (site down, season not
        published yet) - those are expected/frequent and self-heal next run.
        """
        return bool(self.tournament_errors) or any(
            result.clean_error or result.fetch_needs_attention for result in self.results
        )


def _update_one_year(
    tour: Tour,
    year: int,
    *,
    client: TennisDataUKClient,
    raw_dir: Path | None,
    clean_dir: Path | None,
) -> YearUpdateResult:
    """Fetch+checkpoint then clean a single tour/year, recording (not raising) any failure."""
    result = YearUpdateResult(tour=tour.value, year=year)

    try:
        fetch_and_checkpoint_year(tour, year, client=client, raw_dir=raw_dir)
        result.fetched = True
    except TennisDataUKDownloadError as exc:
        # Expected/frequent: site temporarily down, or the season isn't published yet.
        logger.warning(
            "[%s %s] Fetch failed (site down or no data yet): %s",
            tour.value.upper(),
            year,
            exc,
        )
        result.fetch_error = str(exc)
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        # Anything else (e.g. RawCheckpointError - wrong-tour data) is surprising.
        logger.exception("[%s %s] Unexpected error while fetching", tour.value.upper(), year)
        result.fetch_error = str(exc)
        result.fetch_needs_attention = True

    raw_path = raw_checkpoint_path(tour, year, raw_dir)
    if not raw_path.exists():
        return result

    # Re-clean even when today's fetch failed, so a transient outage doesn't
    # stall re-processing whatever raw checkpoint is already on disk (e.g. from
    # last week) - and so last season's checkpoint keeps getting re-cleaned
    # even after this year's fetch starts succeeding.
    try:
        clean_path, rows = _clean_and_write_year(tour, year, raw_dir=raw_dir, clean_dir=clean_dir)
    except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
        logger.error(
            "[%s %s] FAILED to clean - likely needs a known_fixes entry or a "
            "KNOWN_*_YEARS exception: %s",
            tour.value.upper(),
            year,
            exc,
        )
        result.clean_error = str(exc)
        return result

    result.cleaned = True
    result.rows = rows
    logger.info("[%s %s] Wrote %d rows to %s", tour.value.upper(), year, rows, clean_path)
    return result


def update_current_season(
    tours: Iterable[Tour | str] = (Tour.ATP, Tour.WTA),
    years: Iterable[int] | None = None,
    *,
    client: TennisDataUKClient | None = None,
    raw_dir: Path | None = None,
    clean_dir: Path | None = None,
) -> SeasonUpdateReport:
    """Weekly refresh: fetch+checkpoint, clean, and rebuild tournaments, best-effort per tour/year.

    Meant to run unattended on a schedule (see `scripts/uk/weekly_update.py`):
    a download failure (site down, new season not published yet) or a clean
    failure (a new data inconsistency that needs a `known_fixes` entry or a
    `KNOWN_*_YEARS` exception) is recorded per (tour, year) rather than
    aborting the run, so one bad combination never blocks every other one.

    `years` defaults to the current year plus the previous one: the source
    sometimes only finalizes last season's final few tournaments after the
    turn of the year, and the new season's file may not exist yet - checking
    both every run means neither gets silently missed.

    Returns a `SeasonUpdateReport`; check its `.needs_attention` to decide
    whether a human needs to look at anything (see `log_season_update_report`
    for a human-readable rendering of the same report).
    """
    client = client or TennisDataUKClient()
    if years is None:
        current_year = datetime.now().astimezone().year
        years = (current_year - 1, current_year)
    resolved_years = sorted(set(years))
    resolved_tours = [Tour(str(tour).lower()) for tour in tours]

    results = [
        _update_one_year(tour, year, client=client, raw_dir=raw_dir, clean_dir=clean_dir)
        for tour in resolved_tours
        for year in resolved_years
    ]

    report = SeasonUpdateReport(results=results)

    for tour in resolved_tours:
        cleaned_years = [
            result.year for result in results if result.tour == tour.value and result.cleaned
        ]
        if not cleaned_years:
            continue
        try:
            table_path, _, _ = build_uk_tournaments(tour, cleaned_years, clean_dir=clean_dir)
            report.tournament_tables[tour.value] = table_path
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.exception("[%s] Failed to rebuild tournament table", tour.value.upper())
            report.tournament_errors[tour.value] = str(exc)

    return report


def log_season_update_report(report: SeasonUpdateReport) -> None:
    """Log a per tour/year status table, tournament-rebuild results, and an overall verdict."""
    logger.info("=" * 70)
    logger.info("Tennis-Data UK season update")
    logger.info("=" * 70)

    for result in report.results:
        tour_year = f"{result.tour.upper()} {result.year}"
        if result.clean_error:
            logger.error("  %s: NEEDS ATTENTION (clean failed) - %s", tour_year, result.clean_error)
        elif result.fetch_needs_attention:
            logger.error(
                "  %s: NEEDS ATTENTION (fetch failed unexpectedly) - %s",
                tour_year,
                result.fetch_error,
            )
        elif result.cleaned:
            note = "" if result.fetched else " [using previously-fetched raw checkpoint]"
            logger.info("  %s: OK (%d rows)%s", tour_year, result.rows, note)
        elif result.fetch_error:
            logger.warning(
                "  %s: SKIPPED (no data yet / site unavailable) - %s",
                tour_year,
                result.fetch_error,
            )
        else:
            logger.warning("  %s: SKIPPED (no raw checkpoint available)", tour_year)

    for tour, path in report.tournament_tables.items():
        logger.info("  %s tournaments: updated %s", tour.upper(), path)
    for tour, error in report.tournament_errors.items():
        logger.error("  %s tournaments: NEEDS ATTENTION - %s", tour.upper(), error)

    logger.info("=" * 70)
    if report.needs_attention:
        logger.error(
            "Result: NEEDS ATTENTION - see above for what to add to known_fixes/ "
            "or a KNOWN_*_YEARS exception, or review by hand."
        )
    else:
        logger.info("Result: OK")


__all__ = [
    "SeasonUpdateReport",
    "YearUpdateResult",
    "log_season_update_report",
    "update_current_season",
]
