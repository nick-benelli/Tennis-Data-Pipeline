"""Break Sackmann's free-text `score` column into structured per-set features.

Sackmann's `score` is a single string like "6-2 7-5" or "6-3 7-6(10)": one
whitespace-separated token per set, "<winner_games>-<loser_games>", with a
"(<loser_tiebreak_points>)" suffix on any set that went to a tiebreak - only
the *loser's* tiebreak point total is ever recorded, never the winner's.
Retirements/walkovers/defaults end the string early with a marker token
("RET"/"W/O"/"DEF") instead of a final set score.

Turning that into per-set features means recovering the winner's tiebreak
score from the loser's alone. Under the standard "win by 2" tiebreak rule,
that's unambiguous once the breaker has gone past its regular target: the
winner's points are `max(target, loser_points + 2)` for a first-to-`target`
breaker (e.g. loser_points=10 against the usual target=7 gives 12-10, matching
"7-6(10)"). What Sackmann's data *doesn't* tell us is which `target` applied -
regular tiebreaks are first-to-7, but a match's final set can instead be
decided by a first-to-10 "match tiebreak" ("supertiebreak"), depending on the
event and era.

All four Grand Slams adopted a 10-point final-set tiebreak starting in 2022
(https://apnews.com/article/sports-tennis-wimbledon-45807298dbe77ae8805dfe0fbdabb1b8),
which `default_deciding_set_tiebreak_target` encodes - but the years before
that are messier and deliberately *not* modeled here (Wimbledon used a
7-point breaker at 12-12 from 2019-2021; the Australian Open used a 10-point
breaker at 6-6 from 2019; the French Open had no final-set tiebreak at all
until 2022; the US Open has used a 7-point breaker at 6-6 since 1970). Pass
`deciding_set_tiebreak_target` directly to `parse_score`, or override
`build_score_features`'s per-row targets, if older matches need that level of
precision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .tournaments import _SCORE_STATUS_MARKERS

MAX_SETS = 5
REGULAR_TIEBREAK_TARGET = 7
SUPER_TIEBREAK_TARGET = 10
# The first Grand Slam season every major used a 10-point final-set tiebreak.
SUPER_TIEBREAK_SLAM_YEAR = 2022

_SET_TOKEN_RE = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


@dataclass(frozen=True)
class SetScore:
    """One parsed set: games for each side, plus tiebreak points if it went to one."""

    winner_games: int
    loser_games: int
    tiebreak_loser_points: int | None = None
    tiebreak_winner_points: int | None = None


def _tiebreak_winner_points(loser_points: int, target: int) -> int:
    """Winner's breaker points from the loser's, assuming a first-to-`target`-win-by-2 breaker."""
    return max(target, loser_points + 2)


def parse_set_token(token: str) -> SetScore | None:
    """
    Parse one set token (e.g. "7-6(5)").

    Returns None if `token` isn't a set score - a status marker like
    "RET"/"W/O"/"DEF", or any other unparseable junk.
    """
    match = _SET_TOKEN_RE.match(token)
    if not match:
        return None

    winner_games, loser_games, tiebreak_loser = match.groups()
    if tiebreak_loser is None:
        return SetScore(int(winner_games), int(loser_games))

    loser_points = int(tiebreak_loser)
    return SetScore(
        int(winner_games),
        int(loser_games),
        tiebreak_loser_points=loser_points,
        tiebreak_winner_points=_tiebreak_winner_points(loser_points, REGULAR_TIEBREAK_TARGET),
    )


def parse_score(
    score: str | None, *, deciding_set_tiebreak_target: int = REGULAR_TIEBREAK_TARGET
) -> list[SetScore]:
    """Parse a full match score string into one `SetScore` per set actually played.

    Stops at the first token that isn't a set score (a status marker like
    "RET"/"W/O"/"DEF", or unparseable junk) - nothing after that was played.
    If the last parsed set went to a tiebreak, it's re-scored against
    `deciding_set_tiebreak_target` instead of the regular 7-point rule, since
    the last set is the only one that could have been a supertiebreak decider.
    Callers that don't know whether the last set actually was the match's
    decider (e.g. a straight-sets win doesn't reach one) should leave this at
    the default and only pass a non-default target when that's confirmed -
    see `build_score_features`.
    """
    if not isinstance(score, str) or not score.strip():
        return []

    sets: list[SetScore] = []
    for token in score.split():
        parsed = parse_set_token(token)
        if parsed is None:
            break
        sets.append(parsed)

    last_is_tiebreak = sets and sets[-1].tiebreak_loser_points is not None
    if last_is_tiebreak and deciding_set_tiebreak_target != REGULAR_TIEBREAK_TARGET:
        loser_points = sets[-1].tiebreak_loser_points
        assert loser_points is not None  # narrows the type for mypy; checked by `last_is_tiebreak`
        sets[-1] = SetScore(
            sets[-1].winner_games,
            sets[-1].loser_games,
            tiebreak_loser_points=loser_points,
            tiebreak_winner_points=_tiebreak_winner_points(loser_points, deciding_set_tiebreak_target),
        )
    return sets


def default_deciding_set_tiebreak_target(tourney_level: str | None, year: float | int | None) -> int:
    """10 for a Grand Slam (`tourney_level == "G"`) played in/after `SUPER_TIEBREAK_SLAM_YEAR`, else 7.

    See the module docstring: this is deliberately a coarse default, not a
    complete history of every slam's final-set tiebreak rule.
    """
    if tourney_level == "G" and pd.notna(year) and year >= SUPER_TIEBREAK_SLAM_YEAR:
        return SUPER_TIEBREAK_TARGET
    return REGULAR_TIEBREAK_TARGET


def _match_status(score: pd.Series) -> pd.Series:
    """Derive a match-status label from a free-text score column.

    Same rule as `handler.sackmann.tournaments._add_match_status_column`, just
    parameterized on the column itself rather than hardcoded to `df["score"]`.
    """
    score = score.astype("string").fillna("")
    status = pd.Series("completed", index=score.index, dtype="string")
    for marker, label in _SCORE_STATUS_MARKERS:
        status = status.mask(score.str.contains(marker, regex=False), label)
    return status.astype("category")


def build_score_features(
    df: pd.DataFrame,
    *,
    score_col: str = "score",
    best_of_col: str = "best_of",
    tourney_level_col: str = "tourney_level",
    tourney_date_col: str = "tourney_date",
    max_sets: int = MAX_SETS,
) -> pd.DataFrame:
    """Add per-set winner/loser games + tiebreak-point columns, parsed from `score_col`.

    Adds, for `set1` through `set{max_sets}`:
      - `set{i}_winner`/`set{i}_loser`: games won by the match winner/loser in that set.
      - `set{i}_tiebreak_winner`/`set{i}_tiebreak_loser`: breaker points, only
        set for a set that went to a tiebreak.
    Unplayed sets (e.g. `set3_*` for a straight-sets `best_of=3` match) are
    left `pd.NA`.

    Also adds `match_status` (`completed`/`retired`/`walkover`/`defaulted`,
    inferred from `score_col` - see `handler.sackmann.tournaments`) and
    `sets_played` (how many sets `score_col` actually recorded, which can be
    less than `best_of_col` for a straight-sets win, retirement, walkover, or
    default).

    A set is only eligible for `default_deciding_set_tiebreak_target`'s
    supertiebreak target if `best_of_col` confirms it was the match's actual
    deciding set (`sets_played == best_of`) - a match that ends early (e.g.
    2-0 in a best-of-3) never reaches one, even if its last set went to a
    regular tiebreak. `tourney_level_col`/`tourney_date_col` are only used to
    compute that target and can be omitted (falls back to the regular
    7-point rule for every set).
    """
    if tourney_level_col in df.columns and tourney_date_col in df.columns:
        years = df[tourney_date_col].dt.year
        deciding_targets = [
            default_deciding_set_tiebreak_target(level, year)
            for level, year in zip(df[tourney_level_col], years, strict=True)
        ]
    else:
        deciding_targets = [REGULAR_TIEBREAK_TARGET] * len(df)

    best_of = df[best_of_col] if best_of_col in df.columns else pd.Series(pd.NA, index=df.index)

    parsed_matches: list[list[SetScore]] = []
    for score, bo, target in zip(df[score_col], best_of, deciding_targets, strict=True):
        sets = parse_score(score)
        if target != REGULAR_TIEBREAK_TARGET and pd.notna(bo) and len(sets) == int(bo):
            sets = parse_score(score, deciding_set_tiebreak_target=target)
        parsed_matches.append(sets)

    result = df.copy()
    result["match_status"] = _match_status(df[score_col])
    result["sets_played"] = pd.array([len(sets) for sets in parsed_matches], dtype="Int64")

    for i in range(1, max_sets + 1):
        result[f"set{i}_winner"] = _set_column(parsed_matches, i, "winner_games")
        result[f"set{i}_loser"] = _set_column(parsed_matches, i, "loser_games")
        result[f"set{i}_tiebreak_winner"] = _set_column(parsed_matches, i, "tiebreak_winner_points")
        result[f"set{i}_tiebreak_loser"] = _set_column(parsed_matches, i, "tiebreak_loser_points")

    return result


def _set_column(
    parsed_matches: list[list[SetScore]], set_number: int, attr: str
) -> pd.arrays.IntegerArray:
    """Pull one `SetScore` attribute out of set `set_number` (1-based) for every match.

    Returns an `Int64` array, `pd.NA` for any match that didn't reach `set_number`.
    """
    values = [
        getattr(sets[set_number - 1], attr) if len(sets) >= set_number else None
        for sets in parsed_matches
    ]
    return pd.array(values, dtype="Int64")


__all__ = [
    "MAX_SETS",
    "REGULAR_TIEBREAK_TARGET",
    "SUPER_TIEBREAK_TARGET",
    "SetScore",
    "build_score_features",
    "default_deciding_set_tiebreak_target",
    "parse_score",
    "parse_set_token",
]
