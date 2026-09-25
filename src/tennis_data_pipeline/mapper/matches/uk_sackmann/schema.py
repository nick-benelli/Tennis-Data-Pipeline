"""Shared constants for the UK<->Sackmann match-linking pipeline (Pass 0/1/2)."""

from __future__ import annotations

MATCH_METHOD_MANUAL = "manual_override"
MATCH_METHOD_TOURNAMENT_RANK_UNIQUE = "tournament_rank_unique"
MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR = "tournament_round_name_pair"

# Pass 0: the hand-maintained manual-override file's columns. `year` is for the
# file's own bookkeeping/filtering only - both keys already embed the year and
# are matched exactly, so it's never used as a join key.
MANUAL_LINKS_COLUMNS = ["year", "source_match_key", "canonical_match_key"]

# Pass 1: the blocking + exact-match key shared by both sides once
# official_tournament_id is attached and Sackmann's source_year has been
# aliased to "year".
RANK_CANDIDATE_KEY_COLUMNS = ["year", "tour", "official_tournament_id", "winner_rank", "loser_rank"]

CROSSWALK_COLUMNS = [
    "source_match_key",
    "canonical_match_key",
    "official_tournament_id",
    "year",
    "tour",
    "winner_rank",
    "loser_rank",
    "winner_id",
    "loser_id",
    "match_method",
    "review_flag",
    "source_candidate_count",
    "canonical_candidate_count",
    "round_agrees",
    "winner_rank_points_diff",
    "loser_rank_points_diff",
]

# Pass 2: round replaces winner_rank/loser_rank as the hard block, since Pass 2
# exists specifically for rows where rank is missing or disagrees between sources.
NAME_PAIR_KEY_COLUMNS = ["year", "tour", "official_tournament_id", "round"]

NAME_PAIR_CROSSWALK_COLUMNS = [
    "source_match_key",
    "canonical_match_key",
    "official_tournament_id",
    "year",
    "tour",
    "round",
    "winner_id",
    "loser_id",
    "match_method",
    "review_flag",
    "data_quality_flag",
    "source_candidate_count",
    "canonical_candidate_count",
    "round_agrees",
    "winner_rank_agrees",
    "loser_rank_agrees",
]
