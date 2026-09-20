"""Known one-off and category-typo fixes for Tennis-Data UK raw WTA data.

See `known_fixes/_shared.py` for the `MatchFix` contract, and
notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for the
Wikipedia sources backing the single-match fixes below.
"""

from __future__ import annotations

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner.known_fixes._shared import MatchFix


def _fix_us_open_final_2021(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "W1"] = 6


def _fix_adelaide_r1_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "W1"] = 6


def _fix_madrid_sf_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 1]


def _fix_guangzhou_final_2010(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Date"] = "2010-09-19"


def _fix_cincinnati_final_2012(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Date"] = "2012-08-19"


WTA_MATCH_FIXES: list[MatchFix] = [
    MatchFix(
        tour="wta",
        year=2010,
        description=(
            "Guangzhou International Women's Open final (Groth d. Kudryavtseva): "
            "Date missing entirely from the raw source. Tournament ran Sep 13-19, "
            "2010; the final was played on the last day."
        ),
        source_url="https://en.wikipedia.org/wiki/2010_Guangzhou_International_Women%27s_Open",
        match=lambda df: (
            (df["WTA"] == 46)
            & (df["Winner"] == "Groth J.")
            & (df["Loser"] == "Kudryavtseva A.")
            & df["Date"].isna()
        ),
        apply=_fix_guangzhou_final_2010,
    ),
    MatchFix(
        tour="wta",
        year=2012,
        description=(
            "Western & Southern Open (Cincinnati) final (Li N. d. Kerber A.): Date "
            "missing entirely from the raw source. Tournament ran Aug 11-19, 2012; "
            "the women's final was played on the last day."
        ),
        source_url="https://en.wikipedia.org/wiki/2012_Western_%26_Southern_Open_%E2%80%93_Women%27s_singles",
        match=lambda df: (
            (df["WTA"] == 41)
            & (df["Winner"] == "Li N.")
            & (df["Loser"] == "Kerber A.")
            & df["Date"].isna()
        ),
        apply=_fix_cincinnati_final_2012,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "US Open final (Raducanu d. Fernandez): missing W1 (winner's first-set "
            "games). Actual result was 6-4, 6-3 to Raducanu."
        ),
        source_url="https://en.wikipedia.org/wiki/2021_US_Open_%E2%80%93_Women%27s_singles",
        match=lambda df: (
            (df["WTA"] == 44)
            & (df["Winner"] == "Raducanu E.")
            & (df["Loser"] == "Fernandez L.A.")
            & (df["Date"] == "2021-09-11")
        ),
        apply=_fix_us_open_final_2021,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Adelaide International 1st Round (Bogdan d. Boulter): missing W1 "
            "(winner's first-set games). Actual result was 6-3, 6-4 to Bogdan."
        ),
        source_url="https://www.wtatennis.com/tournaments/2014/adelaide/2024/scores/LS025",
        match=lambda df: (
            (df["WTA"] == 3)
            & (df["Winner"] == "Bogdan A.")
            & (df["Loser"] == "Boulter K.")
            & (df["Date"] == "2024-01-08")
        ),
        apply=_fix_adelaide_r1_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Madrid Open semifinal (Sabalenka d. Rybakina): Wsets/Lsets swapped "
            "(recorded 1-2 despite Sabalenka winning sets 2 and 3, 1-6 7-5 7-6)."
        ),
        source_url="https://en.wikipedia.org/wiki/2024_Mutua_Madrid_Open",
        match=lambda df: (
            (df["WTA"] == 20)
            & (df["Winner"] == "Sabalenka A.")
            & (df["Loser"] == "Rybakina E.")
            & (df["Date"] == "2024-05-02")
        ),
        apply=_fix_madrid_sf_2024,
    ),
]


def fix_wta_category_typos(df: pd.DataFrame) -> pd.DataFrame:
    """Fix known WTA raw-data entry errors found across the historical CSVs.

    | Field    | Bad value(s)   | Fix      | Occurrences                          |
    |----------|----------------|----------|--------------------------------------|
    | Tier     | WTA251..WTA276 | WTA250   | 1 each, 2007 (Excel drag-fill typo)  |
    | Comment  | Walkoer        | Walkover | 1, 2007                              |
    | Surface  | Greenset       | Hard     | 31, 2007 (Sunfeast Open)             |
    | Best of  | 5              | 3        | 1, 2007 (Pacific Life Open)          |

    Greenset is a hard-court surface brand name; WTA singles is always best-of-3.

    Must run before `Tier`/`Comment`/`Surface` are cast to `category` dtype,
    since assigning a value that isn't an existing category raises.
    """
    df = df.copy()

    tier_typo = df["Tier"].astype("string").str.fullmatch(r"WTA2[5-7]\d") & df["Tier"].ne("WTA250")
    df.loc[tier_typo.fillna(False), "Tier"] = "WTA250"

    df.loc[df["Comment"] == "Walkoer", "Comment"] = "Walkover"
    df.loc[df["Surface"] == "Greenset", "Surface"] = "Hard"
    df.loc[df["Best of"] != 3, "Best of"] = 3

    return df
