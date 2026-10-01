"""Cleaning utilities for Sackmann match data."""

from __future__ import annotations

import pandas as pd

from .schema import (
    DOUBLES_CATEGORY_COLUMNS,
    DOUBLES_FLOAT_COLUMNS,
    DOUBLES_INT_COLUMNS,
    DOUBLES_STRING_COLUMNS,
    SINGLES_CATEGORY_COLUMNS,
    SINGLES_FLOAT_COLUMNS,
    SINGLES_INT_COLUMNS,
    SINGLES_STRING_COLUMNS,
)


def _parse_tourney_date(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the shared YYYYMMDD tourney_date column in place, if present."""
    if "tourney_date" in df.columns:
        df["tourney_date"] = pd.to_datetime(
            df["tourney_date"].astype("Int64").astype(str),
            format="%Y%m%d",
            errors="coerce",
        )
    return df


def _coerce_columns(
    df: pd.DataFrame,
    *,
    int_columns: tuple[str, ...],
    float_columns: tuple[str, ...],
    string_columns: tuple[str, ...],
    category_columns: tuple[str, ...],
) -> pd.DataFrame:
    """Coerce each present column to its declared dtype, in place."""
    for column in int_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in float_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype("Float64")

    for column in string_columns:
        if column in df.columns:
            df[column] = df[column].astype("string")

    for column in category_columns:
        if column in df.columns:
            df[column] = df[column].astype("category")

    return df


def _add_canonical_match_key(df: pd.DataFrame) -> pd.DataFrame:
    """Add `canonical_match_key` = `tourney_id` + "_" + `match_num`, Sackmann's unique per-match id.

    Round-robin events (e.g. the WTA/ATP season-ending "Tournament of Champions")
    can reuse `match_num` across the round-robin stage and the knockout stage
    within the same `tourney_id` - `round` is appended to disambiguate, but only
    for rows that actually collide, so the key stays the plain
    `tourney_id_match_num` form for every other match.
    """
    key = (df["tourney_id"].astype(str) + "_" + df["match_num"].astype(str)).astype("string")
    collides = key.duplicated(keep=False)
    if collides.any():
        key = key.where(~collides, key + "_" + df["round"].astype(str))
    df["canonical_match_key"] = key
    return df


def sort_chronologically(df: pd.DataFrame) -> pd.DataFrame:
    """Reorder matches to chronological order (tournament start date, then round progression).

    Sackmann's raw archive lists each tournament's matches from the final
    back down to the first round - great for "what happened in the final"
    but awkward for reconstructing a player's path through the draw (e.g.
    looking up what they did in their *previous* round). `match_num` climbs
    with the rounds though (lowest for the first round of a knockout draw or
    round-robin group stage, highest for the final/third-place match),
    so sorting by `tourney_date`, then `tourney_id`, then `match_num`
    restores chronological order without needing to parse `round` codes at all.
    """
    sort_columns = [col for col in ("tourney_date", "tourney_id", "match_num") if col in df.columns]
    if not sort_columns:
        return df
    return df.sort_values(sort_columns, kind="stable").reset_index(drop=True)


def clean_matches(
    df: pd.DataFrame,
    *,
    chronological: bool = False,
) -> pd.DataFrame:
    """Clean Sackmann singles match data (tour-level, qual/challenger, futures).

    Pass `chronological=True` to also reorder rows into chronological order
    (see `sort_chronologically`) - the raw archive otherwise lists each
    tournament's matches final-to-first-round.
    """
    result = _parse_tourney_date(df.copy())
    result = _coerce_columns(
        result,
        int_columns=SINGLES_INT_COLUMNS,
        float_columns=SINGLES_FLOAT_COLUMNS,
        string_columns=SINGLES_STRING_COLUMNS,
        category_columns=SINGLES_CATEGORY_COLUMNS,
    )
    result = _add_canonical_match_key(result)
    if chronological:
        result = sort_chronologically(result)
    return result.reset_index(drop=True)


def clean_doubles_matches(
    df: pd.DataFrame,
    *,
    chronological: bool = False,
) -> pd.DataFrame:
    """Clean Sackmann ATP doubles match data (per-team stats, two players a side).

    Pass `chronological=True` to also reorder rows into chronological order -
    see `clean_matches`.
    """
    result = _parse_tourney_date(df.copy())
    result = _coerce_columns(
        result,
        int_columns=DOUBLES_INT_COLUMNS,
        float_columns=DOUBLES_FLOAT_COLUMNS,
        string_columns=DOUBLES_STRING_COLUMNS,
        category_columns=DOUBLES_CATEGORY_COLUMNS,
    )
    result = _add_canonical_match_key(result)
    if chronological:
        result = sort_chronologically(result)
    return result.reset_index(drop=True)
