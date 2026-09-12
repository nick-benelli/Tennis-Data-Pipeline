"""WTA-specific helpers for Tennis-Data.co.uk."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
from .client import (
    TennisDataUKClient,
    Tour,
)


def load_year(
    year: int,
    *,
    client: TennisDataUKClient | None = None,
) -> pd.DataFrame:
    """Load one WTA season from Tennis-Data.co.uk.

    Parameters
    ----------
    year
        Season year to download.
    client
        Optional preconfigured TennisDataUKClient.

    Returns
    -------
    pandas.DataFrame
        WTA matches for the requested year.
    """
    client = client or TennisDataUKClient()

    return client.load_year(
        year=year,
        tour=Tour.WTA,
    )


def load_years(
    years: Iterable[int],
    *,
    client: TennisDataUKClient | None = None,
) -> pd.DataFrame:
    """Load and combine multiple WTA seasons.

    Parameters
    ----------
    years
        Years to download.
    client
        Optional preconfigured TennisDataUKClient.

    Returns
    -------
    pandas.DataFrame
        Combined WTA match data.
    """
    client = client or TennisDataUKClient()

    frames: list[pd.DataFrame] = []

    for year in years:
        df = load_year(
            year,
            client=client,
        ).copy()

        df["source_year"] = year
        df["tour"] = Tour.WTA.value

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
) -> pd.DataFrame:
    """Load an inclusive range of WTA seasons."""
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year.")

    return load_years(
        range(start_year, end_year + 1),
        client=client,
    )
