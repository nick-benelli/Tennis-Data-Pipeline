"""WTA helpers for the Sackmann archive."""

from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd

from .cleaning import clean_matches
from .client import SackmannClient, Tour
from .schema import MatchLevel


def _load_level_year(
    year: int,
    *,
    loader: Callable[[SackmannClient, int], pd.DataFrame],
    match_level: MatchLevel,
    client: SackmannClient | None,
    clean: bool,
) -> pd.DataFrame:
    """Download and (optionally) clean one WTA season for a given match level."""
    client = client or SackmannClient()

    df = loader(client, year)

    if clean:
        df = clean_matches(df)

    df = df.copy()
    df["source_year"] = year
    df["tour"] = Tour.WTA.value
    df["match_type"] = "singles"
    df["match_level"] = match_level.value

    return df


def _load_level_years(
    years: Iterable[int],
    *,
    loader: Callable[[SackmannClient, int], pd.DataFrame],
    match_level: MatchLevel,
    client: SackmannClient | None,
    clean: bool,
) -> pd.DataFrame:
    """Download and concatenate multiple WTA seasons for a given match level."""
    client = client or SackmannClient()

    frames = [
        _load_level_year(
            year,
            loader=loader,
            match_level=match_level,
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


def _load_level_range(
    start_year: int,
    end_year: int,
    *,
    loader: Callable[[SackmannClient, int], pd.DataFrame],
    match_level: MatchLevel,
    client: SackmannClient | None,
    clean: bool,
) -> pd.DataFrame:
    """Download an inclusive WTA year range for a given match level."""
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year.")

    return _load_level_years(
        range(start_year, end_year + 1),
        loader=loader,
        match_level=match_level,
        client=client,
        clean=clean,
    )


def load_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one WTA season of tour-level singles matches."""
    return _load_level_year(
        year,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.WTA),
        match_level=MatchLevel.MAIN,
        client=client,
        clean=clean,
    )


def load_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple WTA seasons of tour-level singles matches."""
    return _load_level_years(
        years,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.WTA),
        match_level=MatchLevel.MAIN,
        client=client,
        clean=clean,
    )


def load_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive WTA year range of tour-level singles matches."""
    return _load_level_range(
        start_year,
        end_year,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.WTA),
        match_level=MatchLevel.MAIN,
        client=client,
        clean=clean,
    )


def load_qual_itf_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one WTA season of qualifying + ITF singles matches."""
    return _load_level_year(
        year,
        loader=lambda c, y: c.load_wta_qual_itf_matches(y),
        match_level=MatchLevel.QUAL_ITF,
        client=client,
        clean=clean,
    )


def load_qual_itf_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple WTA seasons of qualifying + ITF singles matches."""
    return _load_level_years(
        years,
        loader=lambda c, y: c.load_wta_qual_itf_matches(y),
        match_level=MatchLevel.QUAL_ITF,
        client=client,
        clean=clean,
    )


def load_qual_itf_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive WTA year range of qualifying + ITF singles matches."""
    return _load_level_range(
        start_year,
        end_year,
        loader=lambda c, y: c.load_wta_qual_itf_matches(y),
        match_level=MatchLevel.QUAL_ITF,
        client=client,
        clean=clean,
    )

__all__ = [
    "load_year",
    "load_years",
    "load_range",
    "load_qual_itf_year",
    "load_qual_itf_years",
    "load_qual_itf_range",
]
