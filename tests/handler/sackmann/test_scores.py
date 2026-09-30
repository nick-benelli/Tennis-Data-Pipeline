"""Tests for handler.sackmann.scores (score-string -> per-set feature parsing)."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.handler.sackmann.scores import (
    SetScore,
    build_score_features,
    default_deciding_set_tiebreak_target,
    parse_score,
    parse_set_token,
)


class TestParseSetToken:
    def test_plain_set(self) -> None:
        assert parse_set_token("6-2") == SetScore(6, 2)

    def test_tiebreak_set_low_loser_points(self) -> None:
        # loser_points=5 is below the win-by-2 threshold, so the winner just needs the target (7).
        expected = SetScore(7, 6, tiebreak_loser_points=5, tiebreak_winner_points=7)
        assert parse_set_token("7-6(5)") == expected

    def test_tiebreak_set_extended(self) -> None:
        # loser_points=10 is past the threshold, so the winner needs a 2-point lead: 12-10.
        expected = SetScore(7, 6, tiebreak_loser_points=10, tiebreak_winner_points=12)
        assert parse_set_token("7-6(10)") == expected

    @pytest.mark.parametrize("token", ["RET", "W/O", "DEF", "", "not-a-score"])
    def test_non_set_tokens_return_none(self, token: str) -> None:
        assert parse_set_token(token) is None


class TestParseScore:
    def test_straight_sets(self) -> None:
        assert parse_score("6-2 7-5") == [SetScore(6, 2), SetScore(7, 5)]

    def test_stops_at_retirement_marker(self) -> None:
        assert parse_score("6-2 3-0 RET") == [SetScore(6, 2), SetScore(3, 0)]

    def test_walkover_has_no_sets(self) -> None:
        assert parse_score("W/O") == []

    def test_none_and_blank_have_no_sets(self) -> None:
        assert parse_score(None) == []
        assert parse_score("") == []
        assert parse_score(float("nan")) == []  # type: ignore[arg-type]

    def test_only_the_last_set_uses_the_deciding_target(self) -> None:
        # First set's tiebreak stays on the regular 7-point rule even when a
        # non-default deciding_set_tiebreak_target is supplied for the match.
        sets = parse_score("7-6(5) 6-4 7-6(3)", deciding_set_tiebreak_target=10)
        assert sets[0] == SetScore(7, 6, tiebreak_loser_points=5, tiebreak_winner_points=7)
        assert sets[1] == SetScore(6, 4)
        # Last set: loser_points=3 is ambiguous between a 7-pt (7-3... no, target reached at 7)
        # and 10-pt breaker - with deciding_set_tiebreak_target=10, it resolves to 10-3.
        assert sets[2] == SetScore(7, 6, tiebreak_loser_points=3, tiebreak_winner_points=10)

    def test_low_loser_points_differ_by_target(self) -> None:
        regular = parse_score("6-4 7-6(3)")
        super_tb = parse_score("6-4 7-6(3)", deciding_set_tiebreak_target=10)
        assert regular[-1].tiebreak_winner_points == 7
        assert super_tb[-1].tiebreak_winner_points == 10

    def test_high_loser_points_agree_regardless_of_target(self) -> None:
        # Once loser_points is high enough, win-by-2 gives the same answer under either target.
        regular = parse_score("6-4 7-6(10)")
        super_tb = parse_score("6-4 7-6(10)", deciding_set_tiebreak_target=10)
        assert regular[-1].tiebreak_winner_points == super_tb[-1].tiebreak_winner_points == 12


class TestDefaultDecidingSetTiebreakTarget:
    def test_grand_slam_after_cutover_is_supertiebreak(self) -> None:
        assert default_deciding_set_tiebreak_target("G", 2022) == 10
        assert default_deciding_set_tiebreak_target("G", 2023) == 10

    def test_grand_slam_before_cutover_is_regular(self) -> None:
        assert default_deciding_set_tiebreak_target("G", 2021) == 7

    def test_non_slam_level_is_always_regular(self) -> None:
        assert default_deciding_set_tiebreak_target("A", 2023) == 7
        assert default_deciding_set_tiebreak_target("M", 2023) == 7

    def test_missing_year_is_regular(self) -> None:
        assert default_deciding_set_tiebreak_target("G", pd.NA) == 7


class TestBuildScoreFeatures:
    def _df(self) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "score": [
                    "6-2 6-3",  # bo3 straight sets, no tiebreak
                    "6-4 4-6 7-6(3)",  # bo3 decider reaching a 10-pt Grand Slam supertiebreak (2023)
                    "6-4 4-6 7-6(3)",  # identical score, pre-cutover Grand Slam year -> regular target
                    "6-2 3-0 RET",  # retirement, unfinished 2nd set
                    "W/O",  # walkover, no sets at all
                ],
                "best_of": pd.array([3, 3, 3, 3, 3], dtype="Int64"),
                "tourney_level": ["A", "G", "G", "A", "A"],
                "tourney_date": pd.to_datetime(
                    ["2021-06-01", "2023-06-01", "2021-06-01", "2021-06-01", "2021-06-01"]
                ),
            }
        )

    def test_straight_sets_row(self) -> None:
        result = build_score_features(self._df())
        row = result.iloc[0]
        assert row["match_status"] == "completed"
        assert row["sets_played"] == 2
        assert (row["set1_winner"], row["set1_loser"]) == (6, 2)
        assert (row["set2_winner"], row["set2_loser"]) == (6, 3)
        assert pd.isna(row["set3_winner"]) and pd.isna(row["set3_loser"])
        assert pd.isna(row["set1_tiebreak_winner"]) and pd.isna(row["set2_tiebreak_winner"])

    def test_deciding_set_uses_supertiebreak_target_when_eligible(self) -> None:
        result = build_score_features(self._df())
        row = result.iloc[1]
        assert row["sets_played"] == 3
        assert row["set3_tiebreak_loser"] == 3
        assert row["set3_tiebreak_winner"] == 10  # 2023 Grand Slam decider -> 10-pt supertiebreak

    def test_deciding_set_uses_regular_target_before_cutover(self) -> None:
        result = build_score_features(self._df())
        row = result.iloc[2]
        assert row["set3_tiebreak_loser"] == 3
        assert row["set3_tiebreak_winner"] == 7  # 2021 Grand Slam decider -> still the regular 7-pt rule

    def test_retirement_row(self) -> None:
        result = build_score_features(self._df())
        row = result.iloc[3]
        assert row["match_status"] == "retired"
        assert row["sets_played"] == 2
        assert (row["set2_winner"], row["set2_loser"]) == (3, 0)
        assert pd.isna(row["set3_winner"])

    def test_walkover_row_has_no_sets(self) -> None:
        result = build_score_features(self._df())
        row = result.iloc[4]
        assert row["match_status"] == "walkover"
        assert row["sets_played"] == 0
        assert pd.isna(row["set1_winner"])

    def test_missing_best_of_and_level_columns_fall_back_to_regular_target(self) -> None:
        df = pd.DataFrame({"score": ["6-4 4-6 7-6(3)"]})
        result = build_score_features(df)
        assert result.iloc[0]["set3_tiebreak_winner"] == 7
