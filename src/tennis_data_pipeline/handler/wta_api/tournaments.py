"""Derive a clean tournament-summary table from the WTA tournaments API.

Unlike the Tennis-Data UK and Sackmann sources, this data is already one row
per tournament (no match-level aggregation needed) - this just types/renames
`datasources.wta.WtaApiClient.get_tournaments()` output into a stable schema
for persistence.

`tournament_group_id` (the raw API's `tournamentGroup.id`) is renamed to
`official_tournament_id` here: it's the WTA's own permanent tournament id,
the same one `mapper.tournaments.extract_official_tournament_id` has to infer
from Sackmann's `tourney_number` for the vast majority of tournaments (and
can't recover at all for the M0xx/Olympics-era rows - see that module's
docstring) - this source gives it directly, no extraction/backfill needed.
"""

from __future__ import annotations

import pandas as pd

CLEAN_TOURNAMENT_KEY_COLUMNS = ["tour", "year", "official_tournament_id"]
CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS = [
    "group_name",
    "level",
    "title",
    "surface",
    "in_outdoor",
    "city",
    "country",
    "singles_draw_size",
    "doubles_draw_size",
    "prize_money",
    "start_date",
    "end_date",
    "singles_champion",
]


def build_wta_api_tournament_table(df: pd.DataFrame) -> pd.DataFrame:
    """Clean/type one or more years' raw `WtaApiClient.get_tournaments()` output.

    Adds a `tour="wta"` column, renames `tournament_group_id` to
    `official_tournament_id`, parses `start_date`/`end_date`, and sorts/dedupes
    on the key columns (`tour`/`year`/`official_tournament_id`).
    """
    df = df.rename(columns={"tournament_group_id": "official_tournament_id"}).copy()
    df.insert(0, "tour", "wta")
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])
    df = df.drop_duplicates(subset=CLEAN_TOURNAMENT_KEY_COLUMNS)
    df = df.sort_values(CLEAN_TOURNAMENT_KEY_COLUMNS).reset_index(drop=True)
    return df[CLEAN_TOURNAMENT_KEY_COLUMNS + CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS]


__all__ = [
    "CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS",
    "CLEAN_TOURNAMENT_KEY_COLUMNS",
    "build_wta_api_tournament_table",
]
