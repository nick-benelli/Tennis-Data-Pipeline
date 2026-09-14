"""ATP helpers for the Sackmann archive."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .cleaning import clean_matches
from .client import SackmannClient, Tour


def load_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one ATP season."""
    client = client or SackmannClient()

    df = client.load_matches(
        year=year,
        tour=Tour.ATP,
    )

    if clean:
        df = clean_matches(df)

    df = df.copy()
    df["source_year"] = year
    df["tour"] = Tour.ATP.value

    return df


def load_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple ATP seasons."""
    client = client or SackmannClient()

    frames = [
        load_year(
            year,
            client=client,
            clean=clean,
        )
        for year in years
    ]

    if not frames:
        return pd.DataFrame()

    return pd.concat(
        frames,
        ignore_index=True,
    )


def load_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive ATP year range."""
    if end_year < start_year:
        raise ValueError(
            "end_year must be greater than or equal to start_year."
        )

    return load_years(
        range(start_year, end_year + 1),
        client=client,
        clean=clean,
    )