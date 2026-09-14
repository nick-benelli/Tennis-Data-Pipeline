COLUMN_MAP = {
    "ATP": "uk_tournament_id",
    "Year": "year",
    "Location": "location",
    "Tournament": "tournament_name",
    "Date": "match_date",
    "Series": "series",
    "Court": "indoor_outdoor",
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

ROUND_MAP = {
    "1st Round": "R128",
    "2nd Round": "R64",
    "3rd Round": "R32",
    "4th Round": "R16",
    "Quarterfinals": "QF",
    "Semifinals": "SF",
    "The Final": "F",
    "Round Robin": "RR",
}

SURFACE_MAP = {
    "Hard": "hard",
    "Clay": "clay",
    "Grass": "grass",
    "Carpet": "carpet",
}

COURT_MAP = {
    "Indoor": "indoor",
    "Outdoor": "outdoor",
}

STATUS_MAP = {
    "Completed": "completed",
    "Retired": "retired",
    "Walkover": "walkover",
    "Awarded": "awarded",
    "Disqualified": "disqualified",
}

SERIES_MAP = {
    "ATP250": "atp_250",
    "ATP500": "atp_500",
    "Masters 1000": "masters_1000",
    "Masters Cup": "tour_finals",
    "Grand Slam": "grand_slam",
}

EXPECTED_SURFACES = {"hard", "clay", "grass", "carpet"}
EXPECTED_COURTS = {"indoor", "outdoor"}
EXPECTED_ROUNDS = {"R128", "R64", "R32", "R16", "QF", "SF", "F", "RR"}

# Canonical (post-COLUMN_MAP) odds column names; which bookmakers are present varies by year.
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
    "indoor_outdoor",
    "surface",
    "round",
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
