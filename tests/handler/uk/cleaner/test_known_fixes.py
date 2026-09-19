"""Tests for the known-issue fix registry (MatchFix + category-typo fixes)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.handler.uk.cleaner import known_fixes

PROJECT_DIR = Path(__file__).resolve().parents[4]


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ATP": [1, 1, 2],
            "Winner": ["Player A.", "Player A.", "Player C."],
            "Loser": ["Player B.", "Player D.", "Player D."],
        }
    )


def test_match_fix_applies_when_exactly_one_row_matches() -> None:
    applied: list[bool] = []

    fix = known_fixes.MatchFix(
        tour="atp",
        year=2024,
        description="test fix",
        source_url=None,
        match=lambda df: (df["ATP"] == 2),
        apply=lambda df, mask: applied.append(True),
    )

    fix.apply_to(_sample_df())
    assert applied == [True]


def test_match_fix_raises_when_zero_rows_match() -> None:
    fix = known_fixes.MatchFix(
        tour="atp",
        year=2024,
        description="test fix",
        source_url=None,
        match=lambda df: (df["ATP"] == 999),
        apply=lambda df, mask: None,
    )

    with pytest.raises(ValueError, match="found 0"):
        fix.apply_to(_sample_df())


def test_match_fix_raises_when_multiple_rows_match() -> None:
    fix = known_fixes.MatchFix(
        tour="atp",
        year=2024,
        description="test fix",
        source_url=None,
        match=lambda df: (df["ATP"] == 1),
        apply=lambda df, mask: None,
    )

    with pytest.raises(ValueError, match="found 2"):
        fix.apply_to(_sample_df())


def test_apply_match_fixes_only_applies_matching_tour_and_year() -> None:
    calls: list[str] = []
    df = _sample_df()

    def unique_mask(d: pd.DataFrame) -> pd.Series:
        return (d["ATP"] == 1) & (d["Loser"] == "Player B.")  # matches exactly row 0

    fixes = [
        known_fixes.MatchFix(
            tour="atp", year=2024, description="a", source_url=None,
            match=unique_mask,
            apply=lambda df, mask: calls.append("atp-2024"),
        ),
        known_fixes.MatchFix(
            tour="wta", year=2024, description="b", source_url=None,
            match=unique_mask,
            apply=lambda df, mask: calls.append("wta-2024"),
        ),
        known_fixes.MatchFix(
            tour="atp", year=2023, description="c", source_url=None,
            match=unique_mask,
            apply=lambda df, mask: calls.append("atp-2023"),
        ),
    ]

    known_fixes.apply_match_fixes(df, tour="atp", year=2024, fixes=fixes)
    assert calls == ["atp-2024"]


@pytest.mark.parametrize("fix", known_fixes.ATP_MATCH_FIXES, ids=lambda f: f.description)
def test_atp_match_fixes_still_match_exactly_one_row_in_real_data(fix: known_fixes.MatchFix) -> None:
    path = PROJECT_DIR / "data/raw/uk/atp" / f"uk_atp_singles_raw_{fix.year}.csv"
    if not path.exists():
        pytest.skip(f"no raw checkpoint for {fix.year}")

    df = pd.read_csv(path)
    fix.apply_to(df)  # raises if it no longer matches exactly one row


@pytest.mark.parametrize("fix", known_fixes.WTA_MATCH_FIXES, ids=lambda f: f.description)
def test_wta_match_fixes_still_match_exactly_one_row_in_real_data(fix: known_fixes.MatchFix) -> None:
    path = PROJECT_DIR / "data/raw/uk/wta" / f"uk_wta_singles_raw_{fix.year}.csv"
    if not path.exists():
        pytest.skip(f"no raw checkpoint for {fix.year}")

    df = pd.read_csv(path)
    fix.apply_to(df)  # raises if it no longer matches exactly one row


def test_fix_wta_category_typos() -> None:
    df = pd.DataFrame(
        {
            "Tier": ["WTA250", "WTA263", "Premier"],
            "Comment": ["Completed", "Walkoer", "Retired"],
            "Surface": ["Hard", "Greenset", "Clay"],
            "Best of": [3, 5, 3],
        }
    )

    result = known_fixes.fix_wta_category_typos(df)

    assert list(result["Tier"]) == ["WTA250", "WTA250", "Premier"]
    assert list(result["Comment"]) == ["Completed", "Walkover", "Retired"]
    assert list(result["Surface"]) == ["Hard", "Hard", "Clay"]
    assert list(result["Best of"]) == [3, 3, 3]
