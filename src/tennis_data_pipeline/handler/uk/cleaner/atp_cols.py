"""ATP-specific raw/clean column names, dtypes, and category maps for Tennis-Data UK."""

from tennis_data_pipeline.handler.uk.cleaner import common

COLUMN_MAP = {
    "ATP": "uk_tournament_id",
    "Year": "year",
    "Location": "location",
    "Tournament": "tournament_name",
    "Date": "match_date",
    "Series": "series",
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
    "W4": "winner_set_4_games",
    "L4": "loser_set_4_games",
    "W5": "winner_set_5_games",
    "L5": "loser_set_5_games",
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

ROUND_MAP = dict(common.BASE_ROUND_MAP)

# Raw (pre-COLUMN_MAP) dtypes for common.load_raw_uk_csv(); ATP has no fractional
# rank-points seasons, so ranks/points/set-scores are all nullable ints.
RAW_INT_COLS = [
    "ATP",
    "Year",
    "Best of",
    "WRank",
    "LRank",
    "WPts",
    "LPts",
    "W1",
    "L1",
    "W2",
    "L2",
    "W3",
    "L3",
    "W4",
    "L4",
    "W5",
    "L5",
    "Wsets",
    "Lsets",
]
RAW_CATEGORY_COLS = ["Series", "Court", "Surface", "Round", "Comment"]

ID_COL = "ATP"
# "Best of" deliberately excluded: unlike Tournament/Series/Court/Surface
# (which describe the event itself and must be constant), it's a per-match
# attribute that legitimately varies by round for pre-2008 Masters Series
# events (best-of-5 final, best-of-3 everywhere else) - see
# atp.apply_known_best_of_fixes() for the corresponding value-level fix.
CONSISTENCY_INFO_COLS = ["Tournament", "Series", "Court", "Surface"]

# Years where find_uk_inconsistent_tournaments/find_uk_reused_tournament_ids flag
# known, already-reviewed issues (e.g. two same-week tournaments sharing a raw id).
KNOWN_TOURNAMENT_INCONSISTENCY_YEARS = {2023}
KNOWN_REUSED_TOURNAMENT_ID_YEARS = {2023}

# Re-exported for callers that still reach these via `atp_cols.*`.
SURFACE_MAP = common.SURFACE_MAP
COURT_MAP = common.COURT_MAP
STATUS_MAP = dict(common.BASE_STATUS_MAP)

SERIES_MAP = {
    "ATP250": "atp_250",
    "ATP500": "atp_500",
    "Masters 1000": "masters_1000",
    "Masters Cup": "tour_finals",
    "Grand Slam": "grand_slam",
}

EXPECTED_SURFACES = common.EXPECTED_SURFACES
EXPECTED_ROUNDS = set(common.BASE_EXPECTED_ROUNDS)
ODDS_COLS = common.ODDS_COLS

# Final column layout: provenance/IDs -> event metadata -> players -> rankings ->
# match result -> status -> odds. Human-readable fields first, long technical keys last.
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
