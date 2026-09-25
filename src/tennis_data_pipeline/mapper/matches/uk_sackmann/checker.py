"""
Checker utilities for UK Sackmann match data.
"""

from __future__ import annotations

import pandas as pd


def tournament_linkage_summary(df: pd.DataFrame) -> pd.Series:
    """Summarize tournament ID mapping coverage for a match dataframe."""
    return pd.Series(
        {
            "matches": len(df),
            "mapped": df["official_tournament_id"].notna().sum(),
            "unmapped": df["official_tournament_id"].isna().sum(),
            "coverage": df["official_tournament_id"].notna().mean(),
        }
    )


def linkage_summary(source: pd.DataFrame, links: pd.DataFrame) -> pd.Series:
    """Summarize how many source matches were successfully linked."""
    total = len(source)
    linked = links["source_match_key"].nunique()

    return pd.Series(
        {
            "total_matches": total,
            "linked_matches": linked,
            "unlinked_matches": total - linked,
            "coverage": linked / total,
        }
    )
