"""Raw checkpoint: persist WTA-tournaments-API downloads to disk, unmodified.

A raw checkpoint is byte-for-byte the API's own flattened columns (see
`cleaner.flatten_tournament`) - no renaming, no dtype coercion, no filtering
by level. Re-running a download for a given year overwrites that year's
checkpoint file; nothing downstream depends on it being append-only.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...config import settings
from .client import WtaApiClient

logger = logging.getLogger(__name__)


def raw_checkpoint_path(year: int, raw_dir: Path | None = None) -> Path:
    """Path for one season's raw WTA-tournaments-API checkpoint CSV.

    `raw_dir` defaults to `settings.paths.raw / wta_api.raw_dir_name`
    (config.yaml's `paths.raw_dir` / `wta_api.raw_dir_name`); the filename
    comes from `wta_api.raw_filename_template`.
    """
    wta_api_settings = settings.wta_api

    raw_dir = raw_dir if raw_dir is not None else settings.paths.raw / wta_api_settings.raw_dir_name
    filename = wta_api_settings.raw_filename_template.format(year=year)
    return raw_dir / wta_api_settings.tournament_dir_name / filename


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


def fetch_and_checkpoint(
    year: int,
    *,
    client: WtaApiClient | None = None,
    raw_dir: Path | None = None,
) -> pd.DataFrame:
    """Download one season's tournaments (every level, ITF included) and persist it as-is.

    Returns the downloaded DataFrame (same one that got written to disk).
    """
    client = client or WtaApiClient()
    df = client.get_tournaments(year)

    path = raw_checkpoint_path(year, raw_dir)
    _warn_on_schema_drift(df, path)

    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)

    return df


__all__ = ["fetch_and_checkpoint", "raw_checkpoint_path"]
