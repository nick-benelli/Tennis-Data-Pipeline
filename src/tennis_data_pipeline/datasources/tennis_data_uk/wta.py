"""WTA-specific helpers for Tennis-Data.co.uk."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .cleaning import clean_matches
from .client import TennisDataUKClient, Tour


def load_year(
    year: int,
    *,
    client: TennisDataUKClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one WTA season from Tennis-Data.co.uk.

    Parameters
    ----------
    year
        Season year to download.
    client
        Optional preconfigured TennisDataUKClient.
    clean
        Whether to apply Tennis-Data UK cleaning and normalization.

    Returns
    -------
    pandas.DataFrame
        WTA matches for the requested year.
    """
    client = client or TennisDataUKClient()

    df = client.load_year(
        year=year,
        tour=Tour.WTA,
    )

    if clean:
        df = clean_matches(df)

    df = df.copy()
    df["source_year"] = year
    df["tour"] = Tour.WTA.value

    return df


def load_years(
    years: Iterable[int],
    *,
    client: TennisDataUKClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load and combine multiple WTA seasons."""
    client = client or TennisDataUKClient()

    frames: list[pd.DataFrame] = []

    for year in years:
        df = load_year(
            year=year,
            client=client,
            clean=clean,
        )

        frames.append(df)

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
    client: TennisDataUKClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive range of WTA seasons."""
    if end_year < start_year:
        raise ValueError(
            "end_year must be greater than or equal to start_year."
        )

    return load_years(
        years=range(start_year, end_year + 1),
        client=client,
        clean=clean,
    )