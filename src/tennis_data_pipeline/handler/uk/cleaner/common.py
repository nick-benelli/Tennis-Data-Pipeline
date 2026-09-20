"""Tour-agnostic constants and helpers shared by the ATP/WTA Tennis-Data UK cleaners."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.validator.tournaments import (
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
NUMBERED_ROUNDS_ASCENDING = [
    "1st Round",
    "2nd Round",
    "3rd Round",
    "4th Round",
    "5th Round",
]
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

# Players remaining when a round starts, keyed on the canonical round code.
# "BR" (third-place playoff, WTA only) is mapped to 4: it's contested by the
# two semifinal losers, i.e. the other half of the final four. "RR" (round
# robin) is intentionally omitted here - group size isn't fixed, so it's
# derived per-event instead; see add_players_remaining() below.
ROUND_SIZE_MAP = {
    "R256": 256,
    "R128": 128,
    "R64": 64,
    "R32": 32,
    "R16": 16,
    "QF": 8,
    "SF": 4,
    "F": 2,
    "BR": 4,
}

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
    """Lowercase, strip, and collapse non-alphanumeric runs to a single underscore."""
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def normalize_key_value(series: pd.Series) -> pd.Series:
    """Vectorized `slugify()`: lowercase, strip, and slug-ify a string Series for key-building."""
    return (
        series.astype("string")
        .str.lower()
        .str.strip()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )


def add_players_remaining(df: pd.DataFrame) -> pd.DataFrame:
    """Add `players_remaining`: the bracket size entering this round (2 for a
    final, 4 for a semifinal, 8 for a quarterfinal, doubling per earlier round).

    Round-robin ("RR") has no fixed group size, so it's inferred instead from
    that event's actual matches; see `_infer_round_robin_field_size()`. See
    ROUND_SIZE_MAP above for the third-place-playoff edge case.
    """
    df = df.copy()
    df["players_remaining"] = df["round"].map(ROUND_SIZE_MAP).astype("Int64")

    rr_mask = df["round"] == "RR"
    if rr_mask.any():
        df.loc[rr_mask, "players_remaining"] = _infer_round_robin_field_size(
            df.loc[rr_mask]
        )

    return df


def _infer_round_robin_field_size(rr: pd.DataFrame) -> pd.Series:
    """Infer each round-robin event's true field size (players per group x
    number of groups), robust to alternates who substitute in for a withdrawn
    player mid-event.

    A withdrawal means the substitute (and the player they replaced) each show
    up with fewer matches played than a full group participant, so a plain
    distinct-player count over-counts. Instead: group size = 1 + the most
    matches anyone in the event played (at least one player almost always
    completes their full group without a substitution), and the number of
    groups falls out of the total match count, since a round-robin group of
    size N plays exactly N*(N-1)/2 matches.
    """
    players = pd.concat(
        [
            rr[["source_event_key", "winner_name"]].rename(
                columns={"winner_name": "player"}
            ),
            rr[["source_event_key", "loser_name"]].rename(
                columns={"loser_name": "player"}
            ),
        ]
    )
    matches_played = players.groupby(["source_event_key", "player"]).size()
    group_size = matches_played.groupby(level="source_event_key").max() + 1

    total_matches = rr.groupby("source_event_key").size()
    matches_per_group = group_size * (group_size - 1) // 2
    num_groups = (total_matches / matches_per_group).round()

    field_size = (num_groups * group_size).astype("Int64")
    return rr["source_event_key"].map(field_size).astype("Int64")


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
            r
            for r in NUMBERED_ROUNDS_ASCENDING
            if r in set(df.loc[group_index, "Round"])
        ]
        round_code_map = dict(round_map)
        # Deliberately non-strict: BRACKET_CODES_FROM_QF (5) is always >=
        # rounds_present, and zip's stop-at-shorter is what maps a smaller
        # draw's fewer numbered rounds correctly.
        for code, label in zip(BRACKET_CODES_FROM_QF, reversed(rounds_present)):  # noqa: B905
            round_code_map[label] = code

        df.loc[group_index, "Round"] = df.loc[group_index, "Round"].map(round_code_map)

    df["Round"] = df["Round"].astype("category")
    return df


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    """Add `source_match_key`: a unique per-match key derived from event/date/round/players."""
    df = df.copy()

    winner = normalize_key_value(df["winner_name"])
    loser = normalize_key_value(df["loser_name"])
    match_date = df["match_date"].dt.strftime("%Y-%m-%d")
    # Round is included so a same-day rematch (e.g. a round-robin pairing that
    # meets again in the final) stays unique even if the raw source stamps a
    # whole round-robin event with one date instead of per-match dates.
    round_code = df["round"].astype("string")

    df["source_match_key"] = (
        df["source_event_key"]
        + "_"
        + match_date
        + "_"
        + round_code
        + "_"
        + winner
        + "_"
        + loser
    )

    return df


def fix_bad_odds(
    df: pd.DataFrame, raw_odds_cols: list[str] | None = None
) -> pd.DataFrame:
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
    known_exception_years: AbstractSet[int] = frozenset(),
) -> None:
    """Raise if tournament metadata is inconsistent, unless `year` is a known exception."""
    if year in known_exception_years:
        logger.info(
            "Skipping tournament-consistency check for %s (known exception).", year
        )
        return

    metrics, affected_rows = find_uk_inconsistent_tournaments(
        df,
        key_columns=[id_col, "Year", "Location"],
        info_cols=info_cols,
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
    known_exception_years: AbstractSet[int] = frozenset(),
) -> None:
    """Raise if a tournament id is reused across genuinely different tournaments."""
    if year in known_exception_years:
        logger.info(
            "Skipping reused-tournament-id check for %s (known exception).", year
        )
        return

    metrics, affected_rows = find_uk_reused_tournament_ids(
        df=df,
        id_col=id_col,
        disambiguating_cols=["Location", "Tournament"],
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


def ensure_odds_columns(
    df: pd.DataFrame, odds_cols: list[str] | None = None
) -> pd.DataFrame:
    """Backfill (post-rename) odds columns missing due to bookmaker coverage drift."""
    return ensure_columns(df, odds_cols if odds_cols is not None else ODDS_COLS)


_REQUIRED_CLEAN_COLS = {
    "uk_tournament_id",
    "year",
    "location",
    "tournament_name",
    "match_date",
    "series",
    "is_outdoor",
    "surface",
    "round",
    "players_remaining",
    "best_of",
    "winner_name",
    "loser_name",
    "match_status",
    "source_event_key",
    "source_match_key",
}


def validate_clean_uk_data(
    df: pd.DataFrame,
    *,
    expected_surfaces: set[str],
    expected_rounds: set[str],
    odds_cols: list[str],
    valid_best_of: set[int],
) -> None:
    """Raise ValueError on any data-quality issue found in cleaned UK match data.

    Shared by `atp.validate_clean_uk_atp_data`/`wta.validate_clean_uk_wta_data`;
    `valid_best_of` is the only thing that differs by tour (ATP allows 3 or 5,
    WTA singles is always 3).
    """
    missing_cols = _REQUIRED_CLEAN_COLS - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    unexpected_surfaces = set(df["surface"].dropna().unique()) - expected_surfaces
    if unexpected_surfaces:
        raise ValueError(f"Unexpected surfaces: {sorted(unexpected_surfaces)}")

    unexpected_rounds = set(df["round"].dropna().unique()) - expected_rounds
    if unexpected_rounds:
        raise ValueError(f"Unexpected rounds: {sorted(unexpected_rounds)}")

    missing_players_remaining = df["round"].notna() & df["players_remaining"].isna()
    if missing_players_remaining.any():
        raise ValueError(
            f"{missing_players_remaining.sum()} rows are missing players_remaining."
        )

    invalid_players_remaining = df["players_remaining"].notna() & (
        df["players_remaining"] < 2
    )
    if invalid_players_remaining.any():
        raise ValueError(
            f"{invalid_players_remaining.sum()} rows have players_remaining < 2."
        )

    if df["source_match_key"].duplicated().any():
        raise ValueError("Duplicate source_match_key values found.")

    # Early-season tournaments (e.g. Brisbane, Doha, Auckland, Chennai) often play
    # their first round in late December of the prior calendar year (the exact
    # date varies by year, e.g. Dec 30 in 2013, Dec 31 in 2018); treat any
    # December date in the prior year as valid for the season.
    match_date = df["match_date"]
    if match_date.isna().any():
        raise ValueError(f"{match_date.isna().sum()} rows are missing match_date.")
    valid_year = (df["year"] == match_date.dt.year) | (
        (df["year"] == match_date.dt.year + 1) & (match_date.dt.month == 12)
    )
    # nullable-Int64 `year` compared against a datetime .dt accessor yields pd.NA
    # (not False) when it mismatches, which `.any()` silently skips; fillna(False)
    # forces those NA rows to count as invalid rather than passing unnoticed.
    invalid_year = ~valid_year.fillna(False)
    if invalid_year.any():
        raise ValueError(f"{invalid_year.sum()} rows have year != match_date year.")

    same_player = df["winner_name"] == df["loser_name"]
    if same_player.any():
        raise ValueError(f"{same_player.sum()} rows have identical winner and loser.")

    invalid_best_of = ~df["best_of"].isin(valid_best_of)
    if invalid_best_of.any():
        missing_best_of = df.loc[invalid_best_of, "best_of"].isna().sum()
        unexpected_values = sorted(df.loc[invalid_best_of, "best_of"].dropna().unique())
        raise ValueError(
            f"{invalid_best_of.sum()} rows have an unexpected best_of "
            f"({missing_best_of} missing, unexpected values: {unexpected_values})."
        )

    completed = df["match_status"] == "completed"

    completed_missing_first_set = completed & (
        df["winner_set_1_games"].isna() | df["loser_set_1_games"].isna()
    )
    if completed_missing_first_set.any():
        raise ValueError(
            f"{completed_missing_first_set.sum()} completed matches "
            "are missing first-set scores."
        )

    invalid_completed_sets = (
        completed
        & df["winner_sets"].notna()
        & df["loser_sets"].notna()
        & (df["winner_sets"] <= df["loser_sets"])
    )
    if invalid_completed_sets.any():
        raise ValueError(
            f"{invalid_completed_sets.sum()} completed matches "
            "have winner_sets <= loser_sets."
        )

    for col in odds_cols:
        invalid_odds = df[col].notna() & (df[col] < 1)
        if invalid_odds.any():
            raise ValueError(f"{col} contains {invalid_odds.sum()} odds < 1.")


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
