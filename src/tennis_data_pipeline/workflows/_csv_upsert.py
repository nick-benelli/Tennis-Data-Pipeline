"""Shared CSV-upsert helper for workflow modules that maintain a running keyed table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def upsert_csv(
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


__all__ = ["upsert_csv"]
