"""Cleaning utilities for Tennis-Data.co.uk match data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .schema import COLUMN_MAP, NUMERIC_COLUMNS


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename Tennis-Data UK columns to canonical names."""
    return df.rename(columns=COLUMN_MAP)


def ensure_columns(
    df: pd.DataFrame,
    columns: list[str],
    default: object = np.nan,
) -> pd.DataFrame:
    """Ensure expected columns exist."""
    result = df.copy()

    for column in columns:
        if column not in result.columns:
            result[column] = default

    return result


def clean_numeric(
    series: pd.Series,
    default: float = np.nan,
) -> pd.Series:
    """Coerce a Series to numeric values."""
    return pd.to_numeric(
        series.replace(r"^\s*$", np.nan, regex=True),
        errors="coerce",
    ).fillna(default)


def clean_matches(
    df: pd.DataFrame,
    *,
    drop_incomplete: bool = True,
) -> pd.DataFrame:
    """Clean raw Tennis-Data UK match data.

    Renames columns to their canonical names, parses dates, backfills columns
    missing due to schema drift across seasons (with NaN), and coerces
    numeric fields. Does not reorient players, create targets, or substitute
    one bookmaker's odds for another's.

    Args:
        df: Raw Tennis-Data UK match data for a single season.
        drop_incomplete: If True, drop rows where ``Comment`` is not
            "Completed" (when the column is present). If False, keep all rows.
    """
    result = df.copy()

    # Standardize source column names.
    result = clean_column_names(result)

    # Backfill columns missing due to schema drift (e.g. older/newer bookmaker coverage).
    result = ensure_columns(result, NUMERIC_COLUMNS)

    # Parse dates.
    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(
            result["Date"],
            errors="coerce",
        )

    # Coerce numeric fields (ranks, points, set scores, odds).
    for column in NUMERIC_COLUMNS:
        result[column] = clean_numeric(result[column])

    # Keep completed matches when status is available.
    if drop_incomplete and "Comment" in result.columns:
        comment = result["Comment"].astype(str).str.strip().str.casefold()
        result = result[comment.eq("completed")].copy()

    return result.reset_index(drop=True)

