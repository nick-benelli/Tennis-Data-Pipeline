"""Shared CSV-upsert helper for workflow modules that maintain a running keyed table."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd


def upsert_csv(
    path: Path,
    rows: pd.DataFrame,
    *,
    key_columns: list[str],
    date_columns: list[str] | None = None,
    keep: Literal["first", "last"] = "last",
) -> pd.DataFrame:
    """Merge `rows` into the CSV at `path`, keyed on `key_columns`.

    `keep="last"` (default) means `rows` wins on conflict - the usual case for
    re-cleaned/re-derived data. Pass `keep="first"` when existing rows on disk
    may have been hand-corrected and should never be overwritten by a rerun
    (e.g. a crosswalk a human has edited directly).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = pd.read_csv(path, parse_dates=date_columns or [])
        combined = pd.concat([existing, rows], ignore_index=True)
    else:
        combined = rows

    combined = combined.drop_duplicates(subset=key_columns, keep=keep)

    # A "num_*" column absent from one side of the concat (e.g. a match status
    # that only shows up in some runs) means "none seen", not "unknown".
    count_cols = [c for c in combined.columns if c.startswith("num_")]
    combined[count_cols] = combined[count_cols].fillna(0)

    combined = combined.sort_values(key_columns).reset_index(drop=True)
    combined.to_csv(path, index=False)
    return combined


__all__ = ["upsert_csv"]
