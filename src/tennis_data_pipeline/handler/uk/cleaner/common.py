"""Tour-agnostic constants and helpers shared by the ATP/WTA Tennis-Data UK cleaners."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.validatior.tournaments import (
    find_uk_inconsistent_tournaments,
    find_uk_reused_tournament_ids,
)

logger = logging.getLogger(__name__)

# Raw string columns present (and left untouched) for both tours.
RAW_STRING_COLS = ["Location", "Tournament", "Winner", "Loser"]

# Round codes shared by both tours; each tour's cols module merges in its own
# extras on top (e.g. WTA's "Third Place").
BASE_ROUND_MAP = {
    "Quarterfinals": "QF",
    "Semifinals": "SF",
    "The Final": "F",
    "Round Robin": "RR",
}

# Draw sizes vary a lot (ATP250 ~28-32 players vs. Slams/Masters at 56-128), so a
# raw "Nth Round" label doesn't map to a fixed bracket code. Instead, count
# backward from the quarterfinals per tournament: the last numbered round before
# QF is always effectively "R16", and each earlier numbered round doubles the
# bracket size.
NUMBERED_ROUNDS_ASCENDING = ["1st Round", "2nd Round", "3rd Round", "4th Round", "5th Round"]
BRACKET_CODES_FROM_QF = ["R16", "R32", "R64", "R128", "R256"]

SURFACE_MAP = {
    "Hard": "hard",
    "Clay": "clay",
    "Grass": "grass",
    "Carpet": "carpet",
}

# Only ever "Indoor"/"Outdoor" in the raw data, so a bool fits better than a category.
COURT_MAP = {
    "Indoor": False,
    "Outdoor": True,
}

# Both tours use these; WTA additionally has "Cancelled" (see wta_cols.STATUS_MAP).
BASE_STATUS_MAP = {
    "Completed": "completed",
    "Retired": "retired",
    "Walkover": "walkover",
    "Awarded": "awarded",
    "Disqualified": "disqualified",
}

EXPECTED_SURFACES = {"hard", "clay", "grass", "carpet"}
BASE_EXPECTED_ROUNDS = {"R128", "R64", "R32", "R16", "QF", "SF", "F", "RR"}

# Canonical (post-COLUMN_MAP) odds column names; which bookmakers are present
# varies by year, but these four cover the whole date range for both tours.
ODDS_COLS = [
    "odds_b365_winner",
    "odds_b365_loser",
    "odds_pinnacle_winner",
    "odds_pinnacle_loser",
    "odds_max_winner",
    "odds_max_loser",
    "odds_avg_winner",
    "odds_avg_loser",
]

RAW_ODDS_COLS = ["B365W", "B365L", "PSW", "PSL", "MaxW", "MaxL", "AvgW", "AvgL"]


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_key_value(series: pd.Series) -> pd.Series:
    return (
        series
        .astype("string")
        .str.lower()
        .str.strip()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )


def add_source_event_key(df: pd.DataFrame, id_column: str) -> pd.DataFrame:
    """Add `source_event_key`/`Year`, keyed by the tour's own tournament-id column."""
    df = df.copy()

    # Date format drifts across seasons (e.g. "1/1/23" vs. "2023-01-01").
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
    if "Year" not in list(df.columns):
        df["Year"] = df["Date"].dt.year

    df["source_event_key"] = (
        df["Year"].astype(str)
        + "_"
        + df[id_column].astype(str)
        + "_"
        + df["Location"].map(slugify)
        + "_"
        + df["Tournament"].map(slugify)
    )

    return df


def assign_round_codes(df: pd.DataFrame, round_map: dict[str, str]) -> pd.DataFrame:
    """Map raw 'Nth Round' labels to bracket codes (R16/R32/...) per tournament.

    See NUMBERED_ROUNDS_ASCENDING/BRACKET_CODES_FROM_QF above for why this
    counts backward from the quarterfinals instead of using a fixed mapping.
    """
    df = df.copy()
    df["Round"] = df["Round"].astype(object)

    for _, group_index in df.groupby("source_event_key").groups.items():
        rounds_present = [
            r for r in NUMBERED_ROUNDS_ASCENDING
            if r in set(df.loc[group_index, "Round"])
        ]
        round_code_map = dict(round_map)
        for code, label in zip(BRACKET_CODES_FROM_QF, reversed(rounds_present)):
            round_code_map[label] = code

        df.loc[group_index, "Round"] = df.loc[group_index, "Round"].map(round_code_map)

    df["Round"] = df["Round"].astype("category")
    return df


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    winner = normalize_key_value(df["winner_name"])
    loser = normalize_key_value(df["loser_name"])
    match_date = df["match_date"].dt.strftime("%Y-%m-%d")

    df["source_match_key"] = (
        df["source_event_key"] + "_" + match_date + "_" + winner + "_" + loser
    )

    return df


def fix_bad_odds(df: pd.DataFrame, raw_odds_cols: list[str] | None = None) -> pd.DataFrame:
    """Null out impossible (<1.0) decimal odds instead of guessing the intended value."""
    df = df.copy()
    raw_odds_cols = raw_odds_cols if raw_odds_cols is not None else RAW_ODDS_COLS

    for col in raw_odds_cols:
        if col not in df.columns:
            continue
        bad_odds = df[col] < 1
        bad_count = int(bad_odds.sum())
        if bad_count:
            logger.warning("%s: nulling %d odds < 1", col, bad_count)
            df.loc[bad_odds, col] = pd.NA

    return df


def check_tournament_consistency(
    df: pd.DataFrame,
    year: int,
    *,
    id_col: str,
    info_cols: list[str],
    known_exception_years: set[int] = frozenset(),
) -> None:
    """Raise if tournament metadata is inconsistent, unless `year` is a known exception."""
    if year in known_exception_years:
        logger.info("Skipping tournament-consistency check for %s (known exception).", year)
        return

    metrics, affected_rows = find_uk_inconsistent_tournaments(
        df, key_columns=[id_col, "Year", "Location"], info_cols=info_cols,
    )

    if not metrics.empty and not affected_rows.empty:
        raise ValueError(
            f"{len(metrics)} inconsistent tournament(s) found in {year} "
            f"({len(affected_rows)} row(s) affected)."
        )


def check_reused_tournament_ids(
    df: pd.DataFrame,
    year: int,
    *,
    id_col: str,
    known_exception_years: set[int] = frozenset(),
) -> None:
    """Raise if a tournament id is reused across genuinely different tournaments."""
    if year in known_exception_years:
        logger.info("Skipping reused-tournament-id check for %s (known exception).", year)
        return

    metrics, affected_rows = find_uk_reused_tournament_ids(
        df=df, id_col=id_col, disambiguating_cols=["Location", "Tournament"],
    )

    if not metrics.empty and not affected_rows.empty:
        raise ValueError(
            f"{len(metrics)} reused {id_col} tournament id(s) found in {year} "
            f"({len(affected_rows)} row(s) affected)."
        )


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Backfill (post-rename) columns missing due to schema drift or tour differences.

    Used both for odds columns missing due to bookmaker-coverage drift (e.g.
    Max/Avg odds only start appearing partway through the historical data) and
    for WTA's set_4/set_5 columns, which don't exist in the raw source
    (WTA singles is always best-of-3) but are kept as all-NaN so ATP and WTA
    share the exact same column set.
    """
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            df[col] = float("nan")
    return df


def ensure_odds_columns(df: pd.DataFrame, odds_cols: list[str] | None = None) -> pd.DataFrame:
    """Backfill (post-rename) odds columns missing due to bookmaker coverage drift."""
    return ensure_columns(df, odds_cols if odds_cols is not None else ODDS_COLS)


def load_raw_uk_csv(
    path: Path,
    year: int,
    *,
    int_cols: list[str],
    category_cols: list[str],
    float_cols: list[str] | None = None,
    pre_dtype_hook: Callable[[pd.DataFrame], pd.DataFrame] | None = None,
) -> pd.DataFrame:
    """Safely load one season's raw Tennis-Data UK CSV: parsed dates, proper numeric/category dtypes.

    Still in raw (pre-`COLUMN_MAP`) column names/values otherwise - this is the
    well-typed starting point the tour-specific cleaning in atp.py/wta.py builds
    on, not the final clean output.

    `pre_dtype_hook` runs right after `Date`/`Year` are set but before any
    numeric/category coercion, e.g. WTA's category-typo fixes, which must run
    before the affected raw values are cast to an immutable category dtype.
    """
    if not path.exists():
        raise FileNotFoundError(f"No raw data file for {year}: {path}")

    df = pd.read_csv(path)

    # Date format drifts across seasons (e.g. "1/1/23" vs. "2000-01-03").
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False)
    df["Year"] = year

    if pre_dtype_hook is not None:
        df = pre_dtype_hook(df)

    float_cols = float_cols or []

    # Nullable ints: ranks/points/set-scores are whole numbers but can be
    # missing (e.g. retired matches).
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Everything left over is bookmaker odds; which bookmakers are present varies by year.
    known_cols = {"Date", *RAW_STRING_COLS, *int_cols, *float_cols, *category_cols}
    odds_cols = [col for col in df.columns if col not in known_cols]
    df[odds_cols] = df[odds_cols].apply(pd.to_numeric, errors="coerce")

    for col in category_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df
