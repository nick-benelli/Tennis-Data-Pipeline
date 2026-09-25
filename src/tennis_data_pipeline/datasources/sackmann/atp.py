"""ATP helpers for the Sackmann archive."""

from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd

from .cleaning import clean_doubles_matches, clean_matches
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
    """Download and (optionally) clean one ATP season for a given match level."""
    client = client or SackmannClient()

    df = loader(client, year)

    if clean:
        df = clean_matches(df)

    df = df.copy()
    df["source_year"] = year
    df["tour"] = Tour.ATP.value
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
    """Download and concatenate multiple ATP seasons for a given match level."""
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
    """Download an inclusive ATP year range for a given match level."""
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
    """Load one ATP season of tour-level singles matches."""
    return _load_level_year(
        year,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.ATP),
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
    """Load multiple ATP seasons of tour-level singles matches."""
    return _load_level_years(
        years,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.ATP),
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
    """Load an inclusive ATP year range of tour-level singles matches."""
    return _load_level_range(
        start_year,
        end_year,
        loader=lambda c, y: c.load_matches(year=y, tour=Tour.ATP),
        match_level=MatchLevel.MAIN,
        client=client,
        clean=clean,
    )


def load_qual_chall_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one ATP season of qualifying + Challenger singles matches."""
    return _load_level_year(
        year,
        loader=lambda c, y: c.load_atp_qual_chall_matches(y),
        match_level=MatchLevel.QUAL_CHALL,
        client=client,
        clean=clean,
    )


def load_qual_chall_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple ATP seasons of qualifying + Challenger singles matches."""
    return _load_level_years(
        years,
        loader=lambda c, y: c.load_atp_qual_chall_matches(y),
        match_level=MatchLevel.QUAL_CHALL,
        client=client,
        clean=clean,
    )


def load_qual_chall_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive ATP year range of qualifying + Challenger singles matches."""
    return _load_level_range(
        start_year,
        end_year,
        loader=lambda c, y: c.load_atp_qual_chall_matches(y),
        match_level=MatchLevel.QUAL_CHALL,
        client=client,
        clean=clean,
    )


def load_futures_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one ATP season of Futures/ITF World Tennis Tour singles matches."""
    return _load_level_year(
        year,
        loader=lambda c, y: c.load_atp_futures_matches(y),
        match_level=MatchLevel.FUTURES,
        client=client,
        clean=clean,
    )


def load_futures_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple ATP seasons of Futures/ITF World Tennis Tour singles matches."""
    return _load_level_years(
        years,
        loader=lambda c, y: c.load_atp_futures_matches(y),
        match_level=MatchLevel.FUTURES,
        client=client,
        clean=clean,
    )


def load_futures_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive ATP year range of Futures/ITF World Tennis Tour singles matches."""
    return _load_level_range(
        start_year,
        end_year,
        loader=lambda c, y: c.load_atp_futures_matches(y),
        match_level=MatchLevel.FUTURES,
        client=client,
        clean=clean,
    )


def load_doubles_year(
    year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load one ATP season of doubles matches.

    The archive only has doubles data for 2000-2020 (Sackmann stopped
    collecting it after that); a year outside that range will 404 as a
    SackmannDownloadError.
    """
    client = client or SackmannClient()

    df = client.load_atp_doubles_matches(year)

    if clean:
        df = clean_doubles_matches(df)

    df = df.copy()
    df["source_year"] = year
    df["tour"] = Tour.ATP.value
    df["match_type"] = "doubles"

    return df


def load_doubles_years(
    years: Iterable[int],
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load multiple ATP seasons of doubles matches."""
    client = client or SackmannClient()

    frames = [
        load_doubles_year(
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


def load_doubles_range(
    start_year: int,
    end_year: int,
    *,
    client: SackmannClient | None = None,
    clean: bool = True,
) -> pd.DataFrame:
    """Load an inclusive ATP year range of doubles matches."""
    if end_year < start_year:
        raise ValueError("end_year must be greater than or equal to start_year.")

    return load_doubles_years(
        range(start_year, end_year + 1),
        client=client,
        clean=clean,
    )


__all__ = [
    "load_year",
    "load_years",
    "load_range",
    "load_futures_year",
    "load_futures_years",
    "load_futures_range",
    "load_doubles_year",
    "load_doubles_years",
    "load_doubles_range",
]
