"""Stage 1-2: download from api.wtatennis.com and persist/reload the raw checkpoint.

- "go grab the data from the WTA tournaments API and write the raw snapshot
  CSV" (`fetch_and_checkpoint_year`/`fetch_and_checkpoint_years`). The actual
  download lives in `datasources.wta.WtaApiClient`; the actual
  checkpoint-writing lives in `datasources.wta.checkpoint`.
- "load a raw checkpoint back for inspection, no cleaning" (`load_raw_year`).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...datasources.wta.checkpoint import fetch_and_checkpoint, raw_checkpoint_path
from ...datasources.wta.client import WtaApiClient

logger = logging.getLogger(__name__)


def fetch_and_checkpoint_year(
    year: int,
    *,
    client: WtaApiClient | None = None,
    raw_dir: Path | None = None,
) -> Path:
    """Download one season live and persist it as a raw checkpoint.

    Returns the path the checkpoint CSV was written to.
    """
    client = client or WtaApiClient()

    df = fetch_and_checkpoint(year, client=client, raw_dir=raw_dir)

    path = raw_checkpoint_path(year, raw_dir)
    logger.info("[%s] Wrote %d rows to %s", year, len(df), path)
    return path


def fetch_and_checkpoint_years(
    years: range | list[int],
    *,
    client: WtaApiClient | None = None,
    raw_dir: Path | None = None,
    fail_fast: bool = False,
) -> list[Path]:
    """Download and checkpoint several seasons.

    A bad/missing season is logged and skipped rather than aborting the whole
    batch, unless `fail_fast` is set.
    """
    client = client or WtaApiClient()

    written: list[Path] = []
    for year in years:
        try:
            written.append(fetch_and_checkpoint_year(year, client=client, raw_dir=raw_dir))
        except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.exception("[%s] Failed to fetch/checkpoint", year)
            if fail_fast:
                raise

    return written


def load_raw_year(year: int, *, raw_dir: Path | None = None) -> pd.DataFrame:
    """Load one season's raw checkpoint as-is (no cleaning) - e.g. for a notebook."""
    path = raw_checkpoint_path(year, raw_dir)
    return pd.read_csv(path)


__all__ = [
    "fetch_and_checkpoint_year",
    "fetch_and_checkpoint_years",
    "load_raw_year",
]
