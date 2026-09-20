"""Stage 1-2: download from Tennis-Data.co.uk and persist/reload the raw checkpoint.

- "go grab the data from tennis-data.co.uk and write the raw snapshot CSV"
  (`fetch_and_checkpoint_year`/`fetch_and_checkpoint_years`). The actual
  download lives in `datasources.tennis_data_uk.client.TennisDataUKClient`;
  the actual checkpoint-writing (with the tour/schema-drift sanity checks)
  lives in `datasources.tennis_data_uk.checkpoint`.
- "load a raw checkpoint back for inspection, no cleaning" (`load_raw_year`).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...datasources.tennis_data_uk.checkpoint import (
    fetch_and_checkpoint,
    raw_checkpoint_path,
)
from ...datasources.tennis_data_uk.client import TennisDataUKClient, Tour
from ...handler.uk.cleaner import atp, wta

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
            written.append(fetch_and_checkpoint_year(tour, year, client=client, raw_dir=raw_dir))
        except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.exception("[%s %s] Failed to fetch/checkpoint", tour.value.upper(), year)
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


__all__ = [
    "fetch_and_checkpoint_year",
    "fetch_and_checkpoint_years",
    "load_raw_year",
]
