"""WTA helpers for the Sackmann archive."""

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
    """Load one WTA season from the Sackmann archive.

    Parameters
    ----------
    year
        Season year to download.
    client
        Optional preconfigured SackmannClient.
    clean
        Whether to apply Sackmann cleaning and normalization.

    Returns
    -------
    pandas.DataFrame
        WTA matches for the requested year.
    """
    client = client or SackmannClient()

    df = client.load_matches(
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
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load and combine multiple WTA seasons.

    Parameters
    ----------
    years
        Years to download.
    client
        Optional preconfigured SackmannClient.
    clean
        Whether to apply Sackmann cleaning and normalization.

    Returns
    -------
    pandas.DataFrame
        Combined WTA match data.
    """
    client = client or SackmannClient()

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
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive range of WTA seasons.

    Parameters
    ----------
    start_year
        First season to load.
    end_year
        Last season to load.
    client
        Optional preconfigured SackmannClient.
    clean
        Whether to apply Sackmann cleaning and normalization.

    Returns
    -------
    pandas.DataFrame
        Combined WTA match data for the requested range.

    Raises
    ------
    ValueError
        If end_year is earlier than start_year.
    """
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year.")

    return load_years(
        years=range(start_year, end_year + 1),
        client=client,
        clean=clean,
    )
