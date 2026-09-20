"""File-naming conventions and column schema for Jeff Sackmann's tennis-data GitHub mirror."""

from __future__ import annotations

from enum import StrEnum

# --- File naming ------------------------------------------------------------

MATCH_FILE_TEMPLATE: str = "{tour}_matches_{year}.csv"

# ATP-only file naming for the archive's lower tiers. The mirror does not split
# WTA the same way (its lower tier is one combined wta_matches_qual_itf_{year}.csv).
ATP_MATCHES_QUAL_CHALL_FILE_TEMPLATE: str = "atp_matches_qual_chall_{year}.csv"
ATP_MATCHES_FUTURES_FILE_TEMPLATE: str = "atp_matches_futures_{year}.csv"

# ATP-only; Sackmann stopped collecting doubles after 2020, and the mirror has
# no WTA equivalent. Requesting a year outside 2000-2020 will 404.
ATP_MATCHES_DOUBLES_FILE_TEMPLATE: str = "atp_matches_doubles_{year}.csv"

# WTA-only: qualifying + ITF matches are combined into one file per year,
# unlike ATP's separate qual_chall/futures files.
WTA_MATCHES_QUAL_ITF_FILE_TEMPLATE: str = "wta_matches_qual_itf_{year}.csv"

PLAYER_FILE: dict[str, str] = {
    "atp": "atp_players.csv",
    "wta": "wta_players.csv",
}

RANKINGS_CURRENT_FILE: dict[str, str] = {
    "atp": "atp_rankings_current.csv",
    "wta": "wta_rankings_current.csv",
}


class MatchLevel(StrEnum):
    """Tiers of singles competition covered by the archive's matches CSVs.

    QUAL_CHALL/FUTURES are ATP-only; QUAL_ITF is WTA-only (its qualifying and
    ITF matches are combined into one file, unlike ATP's separate tiers).
    """

    MAIN = "main"
    QUAL_CHALL = "qual_chall"
    FUTURES = "futures"
    QUAL_ITF = "qual_itf"


# --- Column dtypes ------------------------------------------------------------
#
# Two distinct column layouts exist in this archive:
#   - "singles" (49 columns): atp_matches_{year}/atp_matches_qual_chall_{year}/
#     atp_matches_futures_{year}/wta_matches_{year}/wta_matches_qual_itf_{year}.csv
#     - identical layout across every tour/tier/era checked; only the *values*
#     differ (e.g. tourney_level is 'G'/'M'/'A' at tour level but '15'/'25'
#     ITF prize-money codes for futures, round adds 'Q1'-'Q3' for qualifying).
#   - "doubles" (65 columns): atp_matches_doubles_{year}.csv (ATP-only,
#     2000-2020) - stats/seed/entry are per *team* (one 'w_ace' for the
#     pair), but id/name/hand/ht/ioc/age/rank/rank_points are per *player*
#     ('winner1_*'/'winner2_*', 'loser1_*'/'loser2_*').
#
# The two layouts still share a large common core (same column name, same
# target dtype) - e.g. 'best_of', every 'w_*'/'l_*' stat count, 'score'. That
# shared core is factored out below so it's declared (and can be corrected)
# in exactly one place instead of two.
#
# tourney_date is deliberately excluded from all of these: cleaning.py parses
# it separately with an explicit YYYYMMDD format.
#
# Grouped by target dtype (rather than one dict[str, str]) so each astype()
# call in cleaning.py gets a literal dtype string mypy can resolve against
# pandas' overloads. Category/string columns are left with an open value set
# (no fixed enum/category list) on purpose - trying to pin down every
# tourney_level/round/entry code across 50+ years and several competition
# tiers is exactly the kind of brittle validation that breaks the moment the
# mirror adds a new code upstream.

_SHARED_INT_COLUMNS: tuple[str, ...] = (
    "draw_size",
    "match_num",
    "winner_seed",
    "loser_seed",
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
)

_SHARED_STRING_COLUMNS: tuple[str, ...] = (
    "tourney_id",
    "tourney_name",
    "score",
)

_SHARED_CATEGORY_COLUMNS: tuple[str, ...] = (
    "surface",
    "tourney_level",
    "round",
    "winner_entry",
    "loser_entry",
)

SINGLES_INT_COLUMNS: tuple[str, ...] = _SHARED_INT_COLUMNS + (
    "winner_id",
    "winner_ht",
    "loser_id",
    "loser_ht",
    "winner_rank",
    "winner_rank_points",
    "loser_rank",
    "loser_rank_points",
)

SINGLES_FLOAT_COLUMNS: tuple[str, ...] = (
    "winner_age",
    "loser_age",
)

SINGLES_STRING_COLUMNS: tuple[str, ...] = _SHARED_STRING_COLUMNS + (
    "winner_name",
    "loser_name",
)

SINGLES_CATEGORY_COLUMNS: tuple[str, ...] = _SHARED_CATEGORY_COLUMNS + (
    "winner_hand",
    "winner_ioc",
    "loser_hand",
    "loser_ioc",
)

DOUBLES_INT_COLUMNS: tuple[str, ...] = _SHARED_INT_COLUMNS + (
    "winner1_id",
    "winner2_id",
    "loser1_id",
    "loser2_id",
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
)

DOUBLES_FLOAT_COLUMNS: tuple[str, ...] = (
    "winner1_age",
    "winner2_age",
    "loser1_age",
    "loser2_age",
)

DOUBLES_STRING_COLUMNS: tuple[str, ...] = _SHARED_STRING_COLUMNS + (
    "winner1_name",
    "winner2_name",
    "loser1_name",
    "loser2_name",
)

DOUBLES_CATEGORY_COLUMNS: tuple[str, ...] = _SHARED_CATEGORY_COLUMNS + (
    "winner1_hand",
    "winner2_hand",
    "loser1_hand",
    "loser2_hand",
    "winner1_ioc",
    "winner2_ioc",
    "loser1_ioc",
    "loser2_ioc",
)


def _assert_disjoint_dtype_groups(*groups: tuple[str, ...]) -> None:
    """Guard against a column being assigned more than one target dtype by mistake."""
    seen: set[str] = set()
    for group in groups:
        overlap = seen & set(group)
        if overlap:
            raise AssertionError(f"Column(s) assigned more than one dtype: {sorted(overlap)}")
        seen |= set(group)


_assert_disjoint_dtype_groups(
    SINGLES_INT_COLUMNS,
    SINGLES_FLOAT_COLUMNS,
    SINGLES_STRING_COLUMNS,
    SINGLES_CATEGORY_COLUMNS,
)
_assert_disjoint_dtype_groups(
    DOUBLES_INT_COLUMNS,
    DOUBLES_FLOAT_COLUMNS,
    DOUBLES_STRING_COLUMNS,
    DOUBLES_CATEGORY_COLUMNS,
)
