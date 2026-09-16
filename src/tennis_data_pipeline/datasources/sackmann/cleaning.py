"""Cleaning utilities for Sackmann match data."""

from __future__ import annotations

import pandas as pd


def clean_matches(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Clean Sackmann match-level data without altering its semantics."""
    result = df.copy()

    if "tourney_date" in result.columns:
        result["tourney_date"] = pd.to_datetime(
            result["tourney_date"].astype("Int64").astype(str),
            format="%Y%m%d",
            errors="coerce",
        )

    numeric_columns = [
        "winner_rank",
        "loser_rank",
        "winner_rank_points",
        "loser_rank_points",
        "winner_age",
        "loser_age",
        "winner_ht",
        "loser_ht",
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
    ]

    for column in numeric_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column],
                errors="coerce",
            )

    return result.reset_index(drop=True)