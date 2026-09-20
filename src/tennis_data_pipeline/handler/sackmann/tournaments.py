"""Derive a Tennis-Data-UK-like tournament-summary table from Sackmann match data.

Sackmann's archive has no location/city column and no betting odds, and each
tournament only has a single `tourney_date` (its start date) rather than a
per-match date - so `start_date`/`end_date` always come out equal here, unlike
the Tennis-Data UK table where they can span a tournament's full week. There is
also no dedicated match-status column, so `match_status` is inferred from the
free-text `score` column (e.g. "6-2 0-0 RET" -> retired).
"""

from __future__ import annotations

import pandas as pd

from ..uk.cleaner.tournaments import TournamentTable, build_tournament_table

# tourney_id is already unique per season (e.g. "2023-9900"), but "year" is kept
# as its own key column for parity with the Tennis-Data UK table and easier filtering.
CLEAN_TOURNAMENT_KEY_COLUMNS = ["tour", "year", "tourney_id"]
# tourney_number is tourney_id with the year prefix stripped (e.g. "2023-9900" -> 9900),
# kept alongside the full tourney_id for joins/lookups that don't care about the year.
CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS = [
    "tourney_number",
    "tournament_name",
    "tourney_level",
    "surface",
    "best_of",
    "draw_size",
]

# Substrings `score` uses to flag a match that didn't finish normally (checked
# in order; first match wins). Everything else is treated as "completed".
_SCORE_STATUS_MARKERS = [
    ("W/O", "walkover"),
    ("RET", "retired"),
    ("DEF", "defaulted"),
]


def _add_year_and_tourney_number_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Split `tourney_id` ("2023-9900") into `year` (2023) and `tourney_number` ("9900") columns.

    `tourney_number` is kept as a string, not coerced to int: some years/levels
    use non-numeric suffixes (Davis Cup ties like "D002", or "M001"/"O16" in a
    few seasons), and forcing those to numeric would silently turn them into NA.
    """
    df = df.copy()
    parts = df["tourney_id"].astype("string").str.split("-", n=1, expand=True)
    df["year"] = pd.to_numeric(parts[0], errors="coerce").astype("Int64")
    df["tourney_number"] = parts[1]
    return df


def _add_match_status_column(df: pd.DataFrame) -> pd.DataFrame:
    """Derive `match_status` from the free-text `score` column (no dedicated status column exists)."""
    df = df.copy()
    score = df["score"].astype("string").fillna("")
    status = pd.Series("completed", index=df.index, dtype="string")
    for marker, label in _SCORE_STATUS_MARKERS:
        status = status.mask(score.str.contains(marker, regex=False), label)
    df["match_status"] = status
    return df


def build_sackmann_tournament_table(
    df: pd.DataFrame,
    *,
    key_columns: list[str] | None = None,
    attribute_columns: list[str] | None = None,
) -> TournamentTable:
    """`build_tournament_table` for cleaned Sackmann match data.

    Convenience wrapper for the output of `datasources.sackmann.atp`/`wta`
    `load_year(s)`/`load_range` (tour-level singles). Defaults to
    `tour`/`year`/`tourney_id` as the key and `tourney_number`/`tournament_name`/
    `tourney_level`/`surface`/`best_of`/`draw_size` as the attributes, and also
    adds `start_date`/`end_date` (always equal - see module docstring),
    `num_matches`, `num_rounds`, `num_players`, `champion`, `runner_up`,
    `champion_avg_rank`, and one `num_<status>_matches` column per match status
    inferred from `score` (e.g. `num_completed_matches`, `num_retired_matches`,
    `num_walkover_matches`).
    """
    df = df.copy()
    df = df.rename(columns={"tourney_name": "tournament_name"})
    df["surface"] = df["surface"].astype("string").str.lower()
    df = _add_year_and_tourney_number_columns(df)
    df = _add_match_status_column(df)

    return build_tournament_table(
        df,
        key_columns=key_columns or CLEAN_TOURNAMENT_KEY_COLUMNS,
        attribute_columns=attribute_columns or CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS,
        date_column="tourney_date",
        start_date_column="start_date",
        end_date_column="end_date",
        winner_column="winner_name",
        loser_column="loser_name",
        round_column="round",
        match_status_column="match_status",
        rank_column="winner_rank",
    )


__all__ = [
    "CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS",
    "CLEAN_TOURNAMENT_KEY_COLUMNS",
    "build_sackmann_tournament_table",
]
