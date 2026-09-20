"""WTA-specific raw/clean column names, dtypes, and category maps for Tennis-Data UK."""

from tennis_data_pipeline.handler.uk.cleaner import common

COLUMN_MAP = {
    "WTA": "uk_tournament_id",
    "Year": "year",
    "Location": "location",
    "Tournament": "tournament_name",
    "Date": "match_date",
    "Tier": "series",
    "Court": "is_outdoor",
    "Surface": "surface",
    "Round": "round",
    "Best of": "best_of",
    "Winner": "winner_name",
    "Loser": "loser_name",
    "WRank": "winner_rank",
    "LRank": "loser_rank",
    "WPts": "winner_rank_points",
    "LPts": "loser_rank_points",
    "W1": "winner_set_1_games",
    "L1": "loser_set_1_games",
    "W2": "winner_set_2_games",
    "L2": "loser_set_2_games",
    "W3": "winner_set_3_games",
    "L3": "loser_set_3_games",
    "Wsets": "winner_sets",
    "Lsets": "loser_sets",
    "Comment": "match_status",
    "B365W": "odds_b365_winner",
    "B365L": "odds_b365_loser",
    "PSW": "odds_pinnacle_winner",
    "PSL": "odds_pinnacle_loser",
    "MaxW": "odds_max_winner",
    "MaxL": "odds_max_loser",
    "AvgW": "odds_avg_winner",
    "AvgL": "odds_avg_loser",
}

ROUND_MAP = {
    **common.BASE_ROUND_MAP,
    # Third-place playoff, e.g. WTA Finals round-robin ties/Olympics.
    "Third Place": "BR",
}

# Raw (pre-COLUMN_MAP) dtypes for common.load_raw_uk_csv(). WTA singles is
# always best-of-3, so there's no W4/L4/W5/L5. WPts/LPts are kept as plain
# floats (not RAW_INT_COLS): 2007's ranking-points formula produced fractional
# values (e.g. 332.25).
RAW_INT_COLS = [
    "WTA",
    "Year",
    "Best of",
    "WRank",
    "LRank",
    "W1",
    "L1",
    "W2",
    "L2",
    "W3",
    "L3",
    "Wsets",
    "Lsets",
]
RAW_FLOAT_COLS = ["WPts", "LPts"]
RAW_CATEGORY_COLS = ["Tier", "Court", "Surface", "Round", "Comment"]

ID_COL = "WTA"
CONSISTENCY_INFO_COLS = ["Tournament", "Tier", "Court", "Surface", "Best of"]

# Years where find_uk_inconsistent_tournaments/find_uk_reused_tournament_ids flag
# known, already-reviewed issues. None found for WTA yet.
KNOWN_TOURNAMENT_INCONSISTENCY_YEARS: set[int] = set()
KNOWN_REUSED_TOURNAMENT_ID_YEARS: set[int] = set()

# Re-exported for callers that still reach these via `wta_cols.*`.
SURFACE_MAP = common.SURFACE_MAP
COURT_MAP = common.COURT_MAP

STATUS_MAP = {
    **common.BASE_STATUS_MAP,
    "Cancelled": "cancelled",
}

SERIES_MAP = {
    "Grand Slam": "grand_slam",
    "Premier": "premier",
    "International": "international",
    "WTA1000": "wta_1000",
    "WTA500": "wta_500",
    "WTA250": "wta_250",
    "Tier 1": "tier_1",
    "Tier 2": "tier_2",
    "Tier 3": "tier_3",
    "Tier 4": "tier_4",
    "Tour Championships": "tour_championships",
}

EXPECTED_SURFACES = common.EXPECTED_SURFACES
EXPECTED_ROUNDS = common.BASE_EXPECTED_ROUNDS | {"BR"}
ODDS_COLS = common.ODDS_COLS

# Final column layout: provenance/IDs -> event metadata -> players -> rankings ->
# match result -> status -> odds. Human-readable fields first, long technical keys last.
# winner_set_4_games/loser_set_4_games/winner_set_5_games/loser_set_5_games are
# always NaN (WTA singles is always best-of-3) - kept so ATP and WTA share the
# exact same column set; see common.ensure_columns() in wta.py.
COLUMN_ORDER = [
    "source",
    "tour",
    "year",
    "uk_tournament_id",
    "tournament_name",
    "location",
    "match_date",
    "series",
    "is_outdoor",
    "surface",
    "round",
    "players_remaining",
    "best_of",
    "winner_name",
    "loser_name",
    "winner_rank",
    "loser_rank",
    "winner_rank_points",
    "loser_rank_points",
    "winner_sets",
    "loser_sets",
    "winner_set_1_games",
    "loser_set_1_games",
    "winner_set_2_games",
    "loser_set_2_games",
    "winner_set_3_games",
    "loser_set_3_games",
    "winner_set_4_games",
    "loser_set_4_games",
    "winner_set_5_games",
    "loser_set_5_games",
    "match_status",
    *ODDS_COLS,
    "source_event_key",
    "source_match_key",
]
