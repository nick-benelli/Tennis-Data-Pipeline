"""Tests for Tennis-Data UK cleaning utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd

from tennis_data_pipeline.datasources.tennis_data_uk.cleaning import clean_matches
from tennis_data_pipeline.datasources.tennis_data_uk.schema import COLUMN_MAP


def _raw_match_row(**overrides: object) -> dict:
    row = {
        "ATP": 1,
        "Date": "2024-01-15",
        "Series": "ATP250",
        "Winner": "Player A",
        "Loser": "Player B",
        "WRank": "12",
        "LRank": "34",
        "WPts": "1000",
        "LPts": "500",
        "W1": "6",
        "L1": "4",
        "W2": "6",
        "L2": "3",
        "Wsets": "2",
        "Lsets": "0",
        "B365W": "1.50",
        "B365L": "2.60",
        "IWW": "1.55",
        "IWL": "2.50",
        "Comment": "Completed",
    }
    row.update(overrides)
    return row


def test_column_renaming_applies_column_map() -> None:
    result = clean_matches(pd.DataFrame([_raw_match_row()]))
    assert "winner_Name" in result.columns
    assert "Winner" not in result.columns
    assert result.loc[0, "winner_Name"] == "Player A"


def test_iw_odds_mapping_typo_is_fixed() -> None:
    assert COLUMN_MAP["IWW"] == "winner_IW_odds"

    result = clean_matches(pd.DataFrame([_raw_match_row()]))
    assert "winner_IW_odds" in result.columns
    assert result.loc[0, "winner_IW_odds"] == 1.55


def test_date_parsing() -> None:
    result = clean_matches(pd.DataFrame([_raw_match_row()]))
    assert pd.api.types.is_datetime64_any_dtype(result["Date"])


def test_numeric_coercion_handles_blank_and_invalid_values() -> None:
    row = _raw_match_row(WRank=" ", B365W="not-a-number")
    result = clean_matches(pd.DataFrame([row]))

    assert pd.api.types.is_float_dtype(result["winner_Rank"])
    assert np.isnan(result.loc[0, "winner_Rank"])
    assert np.isnan(result.loc[0, "winner_B365_odds"])


def test_missing_historical_bookmaker_column_becomes_nan() -> None:
    row = _raw_match_row()
    del row["IWW"]
    del row["IWL"]

    result = clean_matches(pd.DataFrame([row]))

    assert "winner_IW_odds" in result.columns
    assert np.isnan(result.loc[0, "winner_IW_odds"])


def test_missing_bookmaker_odds_are_not_substituted_from_other_bookmakers() -> None:
    row = _raw_match_row(PSW="1.60", PSL="2.40")
    del row["B365W"]
    del row["B365L"]

    result = clean_matches(pd.DataFrame([row]))

    assert np.isnan(result.loc[0, "winner_B365_odds"])
    assert result.loc[0, "winner_PS_odds"] == 1.60


def test_completed_match_filter_drops_incomplete_rows() -> None:
    df = pd.DataFrame([_raw_match_row(), _raw_match_row(Comment="Retired")])
    result = clean_matches(df)
    assert len(result) == 1


def test_completed_match_filter_is_case_and_whitespace_insensitive() -> None:
    df = pd.DataFrame([_raw_match_row(Comment=" completed ")])
    result = clean_matches(df)
    assert len(result) == 1


def test_drop_incomplete_false_keeps_all_rows() -> None:
    df = pd.DataFrame([_raw_match_row(), _raw_match_row(Comment="Retired")])
    result = clean_matches(df, drop_incomplete=False)
    assert len(result) == 2


def test_missing_comment_column_does_not_raise() -> None:
    row = _raw_match_row()
    del row["Comment"]
    result = clean_matches(pd.DataFrame([row]))
    assert len(result) == 1
