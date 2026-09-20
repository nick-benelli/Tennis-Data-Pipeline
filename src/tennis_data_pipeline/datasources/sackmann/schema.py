"""File-naming conventions and column schema for Jeff Sackmann's tennis-data GitHub mirror."""

from __future__ import annotations

from enum import StrEnum

MATCH_FILE_TEMPLATE = "{tour}_matches_{year}.csv"

# ATP-only file naming for the archive's lower tiers. The mirror does not split
# WTA the same way (its lower tier is one combined wta_matches_qual_itf_{year}.csv).
ATP_MATCHES_QUAL_CHALL_FILE_TEMPLATE = "atp_matches_qual_chall_{year}.csv"
ATP_MATCHES_FUTURES_FILE_TEMPLATE = "atp_matches_futures_{year}.csv"

# ATP-only; Sackmann stopped collecting doubles after 2020, and the mirror has
# no WTA equivalent. Requesting a year outside 2000-2020 will 404.
ATP_MATCHES_DOUBLES_FILE_TEMPLATE = "atp_matches_doubles_{year}.csv"

PLAYER_FILE = {
    "atp": "atp_players.csv",
    "wta": "wta_players.csv",
}

RANKINGS_CURRENT_FILE = {
    "atp": "atp_rankings_current.csv",
    "wta": "wta_rankings_current.csv",
}


class MatchLevel(StrEnum):
    """Tiers of ATP singles competition covered by the archive's matches CSVs."""

    MAIN = "main"
    QUAL_CHALL = "qual_chall"
    FUTURES = "futures"


# Column dtypes shared by atp_matches_{year}.csv, atp_matches_qual_chall_{year}.csv,
# and atp_matches_futures_{year}.csv - all three files use the identical 49-column
# layout; only the *values* differ by level (e.g. tourney_level is 'G'/'M'/'A' at
# tour level but '15'/'25' ITF prize-money codes for futures, and round adds
# 'Q1'-'Q3' qualifying rounds). This also matches wta_matches_{year}.csv.
# tourney_date is deliberately excluded: cleaning.clean_matches() parses it
# separately with an explicit YYYYMMDD format.
# Grouped by target dtype (rather than one dict[str, str]) so each astype() call
# in cleaning.py gets a literal dtype string mypy can resolve against pandas'
# overloads. Category/string columns are left with an open value set (no fixed
# enum/category list) on purpose - trying to pin down every tourney_level/round/
# entry code across 50+ years and three competition tiers is exactly the kind of
# brittle validation that breaks the moment the mirror adds a new code upstream.
MATCH_INT_COLUMNS = (
    "draw_size",
    "match_num",
    "winner_id",
    "winner_seed",
    "winner_ht",
    "loser_id",
    "loser_seed",
    "loser_ht",
    "best_of",
    "minutes",
    "w_ace",
    "w_df",
    "w_svpt",
    "w_1stIn",
    "w_1stWon",
    "w_2ndWon",
    "w_SvGms",
    "w_bpSaved",
    "w_bpFaced",
    "l_ace",
    "l_df",
    "l_svpt",
    "l_1stIn",
    "l_1stWon",
    "l_2ndWon",
    "l_SvGms",
    "l_bpSaved",
    "l_bpFaced",
    "winner_rank",
    "winner_rank_points",
    "loser_rank",
    "loser_rank_points",
)

MATCH_FLOAT_COLUMNS = (
    "winner_age",
    "loser_age",
)

MATCH_STRING_COLUMNS = (
    "tourney_id",
    "tourney_name",
    "winner_name",
    "loser_name",
    "score",
)

MATCH_CATEGORY_COLUMNS = (
    "surface",
    "tourney_level",
    "winner_entry",
    "winner_hand",
    "winner_ioc",
    "loser_entry",
    "loser_hand",
    "loser_ioc",
    "round",
)

# atp_matches_doubles_{year}.csv has a different 65-column layout from the
# singles files above: stats/seed/entry are per *team* (one 'w_ace' for the
# pair), but id/name/hand/ht/ioc/age/rank/rank_points are per *player*
# ('winner1_*'/'winner2_*', 'loser1_*'/'loser2_*').
DOUBLES_INT_COLUMNS = (
    "draw_size",
    "match_num",
    "winner1_id",
    "winner2_id",
    "winner_seed",
    "loser1_id",
    "loser2_id",
    "loser_seed",
    "best_of",
    "winner1_ht",
    "winner2_ht",
    "loser1_ht",
    "loser2_ht",
    "winner1_rank",
    "winner1_rank_points",
    "winner2_rank",
    "winner2_rank_points",
    "loser1_rank",
    "loser1_rank_points",
    "loser2_rank",
    "loser2_rank_points",
    "minutes",
    "w_ace",
    "w_df",
    "w_svpt",
    "w_1stIn",
    "w_1stWon",
    "w_2ndWon",
    "w_SvGms",
    "w_bpSaved",
    "w_bpFaced",
    "l_ace",
    "l_df",
    "l_svpt",
    "l_1stIn",
    "l_1stWon",
    "l_2ndWon",
    "l_SvGms",
    "l_bpSaved",
    "l_bpFaced",
)

DOUBLES_FLOAT_COLUMNS = (
    "winner1_age",
    "winner2_age",
    "loser1_age",
    "loser2_age",
)

DOUBLES_STRING_COLUMNS = (
    "tourney_id",
    "tourney_name",
    "score",
    "winner1_name",
    "winner2_name",
    "loser1_name",
    "loser2_name",
)

DOUBLES_CATEGORY_COLUMNS = (
    "surface",
    "tourney_level",
    "round",
    "winner_entry",
    "loser_entry",
    "winner1_hand",
    "winner2_hand",
    "loser1_hand",
    "loser2_hand",
    "winner1_ioc",
    "winner2_ioc",
    "loser1_ioc",
    "loser2_ioc",
)
