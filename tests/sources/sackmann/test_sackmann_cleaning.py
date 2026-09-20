"""Tests for Sackmann match-data dtype coercion (clean_matches/clean_doubles_matches)."""

from __future__ import annotations

import pandas as pd

from tennis_data_pipeline.datasources.sackmann.cleaning import clean_doubles_matches, clean_matches

_RAW_ROW = {
    "tourney_id": "2026-9900",
    "tourney_name": "United Cup",
    "surface": "Hard",
    "draw_size": "18",
    "tourney_level": "A",
    "tourney_date": "20260105",
    "match_num": "400",
    "winner_id": "128034",
    "winner_seed": "9",
    "winner_entry": "",
    "winner_name": "Hubert Hurkacz",
    "winner_hand": "R",
    "winner_ht": "196",
    "winner_ioc": "POL",
    "winner_age": "28.8",
    "loser_id": "104527",
    "loser_seed": "16",
    "loser_entry": "",
    "loser_name": "Stan Wawrinka",
    "loser_hand": "R",
    "loser_ht": "183",
    "loser_ioc": "SUI",
    "loser_age": "40.7",
    "score": "6-3 3-6 6-3",
    "best_of": "3",
    "round": "F",
    "minutes": "114",
    "w_ace": "18",
    "w_df": "0",
    "winner_rank": "9",
    "winner_rank_points": "710",
    "loser_rank": "156",
    "loser_rank_points": "397",
}


def test_clean_matches_coerces_expected_dtypes() -> None:
    """Each MATCH_COLUMN_DTYPES entry is cast to its declared dtype."""
    df = clean_matches(pd.DataFrame([_RAW_ROW]))

    assert pd.api.types.is_datetime64_any_dtype(df["tourney_date"])
    assert isinstance(df["surface"].dtype, pd.CategoricalDtype)
    assert isinstance(df["tourney_level"].dtype, pd.CategoricalDtype)
    assert isinstance(df["round"].dtype, pd.CategoricalDtype)
    assert df["draw_size"].dtype == "Int64"
    assert df["w_ace"].dtype == "Int64"
    assert df["winner_rank"].dtype == "Int64"
    assert df["winner_age"].dtype == "Float64"
    assert df["tourney_name"].dtype == "string"


def test_clean_matches_handles_missing_stat_columns() -> None:
    """Older seasons/lower tiers may omit some stat columns entirely; no KeyError."""
    row = {k: v for k, v in _RAW_ROW.items() if k not in {"w_ace", "w_df"}}

    df = clean_matches(pd.DataFrame([row]))

    assert "w_ace" not in df.columns


def test_clean_matches_coerces_blank_numeric_to_na() -> None:
    """Blank numeric fields (common for unranked/unseeded futures players) become NA, not an error."""
    row = dict(_RAW_ROW, winner_seed="", loser_rank="")

    df = clean_matches(pd.DataFrame([row]))

    assert pd.isna(df.loc[0, "winner_seed"])
    assert pd.isna(df.loc[0, "loser_rank"])


_RAW_DOUBLES_ROW = {
    "tourney_id": "2018-M020",
    "tourney_name": "Brisbane",
    "surface": "Hard",
    "draw_size": "32",
    "tourney_level": "A",
    "tourney_date": "20180101",
    "match_num": "269",
    "winner1_id": "105573",
    "winner2_id": "105188",
    "winner_seed": "1",
    "winner_entry": "",
    "loser1_id": "104919",
    "loser2_id": "104547",
    "loser_seed": "",
    "loser_entry": "",
    "score": "3-6 6-3 (10-2)",
    "best_of": "3",
    "round": "F",
    "winner1_name": "Henri Kontinen",
    "winner1_hand": "R",
    "winner1_ht": "",
    "winner1_ioc": "FIN",
    "winner1_age": "27.537303217",
    "winner2_name": "John Peers",
    "winner2_hand": "R",
    "winner2_ht": "",
    "winner2_ioc": "AUS",
    "winner2_age": "29.4373716632",
    "loser1_name": "Leonardo Mayer",
    "loser1_hand": "R",
    "loser1_ht": "188",
    "loser1_ioc": "ARG",
    "loser1_age": "30.6338124572",
    "loser2_name": "Horacio Zeballos",
    "loser2_hand": "L",
    "loser2_ht": "188",
    "loser2_ioc": "ARG",
    "loser2_age": "32.681724846",
    "winner1_rank": "3",
    "winner1_rank_points": "8540",
    "winner2_rank": "4",
    "winner2_rank_points": "8540",
    "loser1_rank": "155",
    "loser1_rank_points": "469",
    "loser2_rank": "38",
    "loser2_rank_points": "1813",
    "minutes": "70",
    "w_ace": "2",
    "w_df": "5",
}


def test_clean_doubles_matches_coerces_expected_dtypes() -> None:
    """Doubles rows use the per-team/per-player doubles column groups, not the singles ones."""
    df = clean_doubles_matches(pd.DataFrame([_RAW_DOUBLES_ROW]))

    assert pd.api.types.is_datetime64_any_dtype(df["tourney_date"])
    assert isinstance(df["surface"].dtype, pd.CategoricalDtype)
    assert isinstance(df["winner1_hand"].dtype, pd.CategoricalDtype)
    assert df["winner1_id"].dtype == "Int64"
    assert df["winner1_age"].dtype == "Float64"
    assert df["winner1_name"].dtype == "string"
    # Blank height (common pre-2010s) becomes NA rather than raising.
    assert pd.isna(df.loc[0, "winner1_ht"])


def test_clean_doubles_matches_does_not_touch_singles_only_columns() -> None:
    """Doubles data has no singular winner_id/winner_name; cleaning must not require them."""
    df = clean_doubles_matches(pd.DataFrame([_RAW_DOUBLES_ROW]))

    assert "winner_id" not in df.columns
    assert "winner_name" not in df.columns
