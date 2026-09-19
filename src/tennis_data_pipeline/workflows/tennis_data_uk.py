"""High-level Tennis-Data UK workflows: download + Stage-2 raw checkpoint.

This is the easy, one-call entry point for "go grab the data from
tennis-data.co.uk and write the raw snapshot CSV". The actual download lives
in `datasources.tennis_data_uk.client.TennisDataUKClient`; the actual
checkpoint-writing (with the tour/schema-drift sanity checks) lives in
`datasources.tennis_data_uk.checkpoint`. This module just wires the two
together with sensible defaults so callers don't need to think about either.

    from tennis_data_pipeline.workflows.tennis_data_uk import fetch_and_checkpoint_years

    fetch_and_checkpoint_years("atp", range(2020, 2025))
    fetch_and_checkpoint_years("wta", [2023, 2024])

Paths default to `settings.paths.raw / "tennis-data-uk" / <tour>` (configure
via config.yaml's `paths.raw_dir`, or the TENNIS_DATA_PIPELINE_RAW_DIR env var).
"""

from __future__ import annotations

import logging
from pathlib import Path

from ..datasources.tennis_data_uk.checkpoint import fetch_and_checkpoint, raw_checkpoint_path
from ..datasources.tennis_data_uk.client import TennisDataUKClient, Tour

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
            logger.exception("[%s %s] Failed to fetch/checkpoint", tour.value.upper(), year)
            if fail_fast:
                raise

    return written


__all__ = ["fetch_and_checkpoint_year", "fetch_and_checkpoint_years"]
