"""Known one-off and category-level data-error fixes for Tennis-Data UK raw data.

Two separate mechanisms, deliberately not unified:

- `MatchFix` - a hand-verified correction to exactly one match. Every fix must
  assert it still matches exactly one row before applying; a fix that
  silently matches zero rows after a future re-scrape or column rename is a
  bug we want to hear about immediately, not one that quietly stops applying.
- Category-typo fixes (e.g. `fix_wta_category_typos`) - a whole mislabeled
  *value* across many rows, which doesn't fit the single-match shape above.

See notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for the
Wikipedia sources backing the ATP single-match fixes below.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class MatchFix:
    """A hand-verified, single-match correction to raw source data."""

    tour: str
    year: int
    description: str
    source_url: str | None
    match: Callable[[pd.DataFrame], pd.Series]
    apply: Callable[[pd.DataFrame, pd.Series], None]

    def apply_to(self, df: pd.DataFrame) -> None:
        """Apply this fix in place, raising if it no longer matches exactly one row."""
        mask = self.match(df)
        matched = int(mask.sum())
        if matched != 1:
            raise ValueError(
                f"Expected exactly 1 row for known fix '{self.description}' "
                f"({self.tour} {self.year}), found {matched}. The raw source "
                "may have changed; review before re-applying this fix."
            )
        self.apply(df, mask)


def apply_match_fixes(df: pd.DataFrame, tour: str, year: int, fixes: list[MatchFix]) -> pd.DataFrame:
    """Apply every registered single-match fix for `tour`/`year`, on a copy."""
    df = df.copy()
    for fix in fixes:
        if fix.tour == tour and fix.year == year:
            fix.apply_to(df)
    return df


def _fix_metz_final_2019(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["W1", "L1", "W2", "L2", "W3", "L3"]] = [6, 7, 7, 6, 6, 3]
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 1]


def _fix_nottingham_sf_2015(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Comment"] = "Retired"


def _fix_montpellier_final_2020(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "ATP"] = 6


def _fix_bogota_final_2013(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 0]


ATP_MATCH_FIXES: list[MatchFix] = [
    MatchFix(
        tour="atp",
        year=2019,
        description="Metz final (Tsonga d. Bedene): corrupted set-2 score, missing set 3 entirely",
        source_url="https://en.wikipedia.org/wiki/2019_Moselle_Open",
        match=lambda df: (
            (df["ATP"] == 53)
            & (df["Winner"] == "Tsonga J.W.")
            & (df["Loser"] == "Bedene A.")
            & (df["Date"] == "2019-09-22")
        ),
        apply=_fix_metz_final_2019,
    ),
    MatchFix(
        tour="atp",
        year=2015,
        description=(
            "Nottingham (AEGON Open) semifinal (Istomin d. Baghdatis): labeled "
            "Completed despite only a single incomplete set (1-2) recorded"
        ),
        source_url=None,
        match=lambda df: (
            (df["ATP"] == 38)
            & (df["Winner"] == "Istomin D.")
            & (df["Loser"] == "Baghdatis M.")
            & (df["Date"] == "2015-06-26")
        ),
        apply=_fix_nottingham_sf_2015,
    ),
    MatchFix(
        tour="atp",
        year=2013,
        description=(
            "Bogota (Claro Open Colombia) final (Karlovic d. Falla): Wsets/Lsets "
            "both recorded as 0 despite two straight sets being recorded"
        ),
        source_url="https://en.wikipedia.org/wiki/2013_Claro_Open_Colombia",
        match=lambda df: (
            (df["ATP"] == 41)
            & (df["Winner"] == "Karlovic I.")
            & (df["Loser"] == "Falla A.")
            & (df["Date"] == "2013-07-21")
        ),
        apply=_fix_bogota_final_2013,
    ),
    MatchFix(
        tour="atp",
        year=2020,
        description=(
            "Montpellier (Open Sud de France) final (Monfils d. Pospisil): raw source "
            "mislabels ATP id as 7 (Pune's id that season); every other Montpellier row is 6"
        ),
        source_url="https://en.wikipedia.org/wiki/2020_Open_Sud_de_France",
        match=lambda df: (
            (df["ATP"] == 7)
            & (df["Winner"] == "Monfils G.")
            & (df["Loser"] == "Pospisil V.")
            & (df["Date"] == "2020-02-09")
        ),
        apply=_fix_montpellier_final_2020,
    ),
]

def _fix_us_open_final_2021(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "W1"] = 6


def _fix_adelaide_r1_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "W1"] = 6


def _fix_madrid_sf_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 1]


WTA_MATCH_FIXES: list[MatchFix] = [
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

    | Field    | Bad value(s)   | Fix      | Occurrences                              |
    |----------|----------------|----------|-------------------------------------------|
    | Tier     | WTA251..WTA276 | WTA250   | 1 each, 2007 (Excel drag-fill artifact)   |
    | Comment  | Walkoer        | Walkover | 1, 2007                                   |
    | Surface  | Greenset       | Hard     | 31, 2007 (Sunfeast Open; a hard-court brand) |
    | Best of  | 5              | 3        | 1, 2007 (Pacific Life Open; WTA singles is always best-of-3) |

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
