"""Known one-off and category-typo fixes for Tennis-Data UK raw ATP data.

See `known_fixes/_shared.py` for the `MatchFix` contract, and
notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for the
Wikipedia sources backing the single-match fixes below.
"""

from __future__ import annotations

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner.known_fixes._shared import (
    MatchFix,
    set_values,
)


def _fix_metz_final_2019(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["W1", "L1", "W2", "L2", "W3", "L3"]] = [6, 7, 7, 6, 6, 3]
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 1]


def _fix_nottingham_sf_2015(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Comment"] = "Retired"


def _fix_montpellier_final_2020(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "ATP"] = 6


def _fix_bogota_final_2013(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["Wsets", "Lsets"]] = [2, 0]


def _fix_memphis_r2_2001(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["W3", "L3", "Wsets", "Lsets"]] = [7, 6, 2, 1]


def _fix_paris_final_2006(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Date"] = "2006-11-05"


def _fix_french_open_r1_2007(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Wsets"] = 3


def _fix_bastad_final_2009(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, ["W1", "L1", "W2", "L2"]] = [6, 3, 7, 6]


def _fix_gstaad_final_2006(df: pd.DataFrame, mask: pd.Series) -> None:
    # Genuinely best-of-5 despite being a regular (non-Masters, non-Slam) event -
    # a verified exception to apply_known_best_of_fixes()'s always-best-of-3 rule.
    set_values(
        df,
        mask,
        {
            "W1": 7,
            "L1": 6,
            "W2": 6,
            "L2": 7,
            "W3": 6,
            "L3": 3,
            "W4": 6,
            "L4": 3,
            "Wsets": 3,
            "Lsets": 1,
            "Best of": 5,
        },
    )


ATP_MATCH_FIXES: list[MatchFix] = [
    MatchFix(
        tour="atp",
        year=2001,
        description=(
            "Memphis (Kroger St. Jude) 2nd Round (Lareau d. Lapentti): 3rd set "
            "score missing entirely from the raw source (Wsets/Lsets recorded as "
            "1-1 despite a 'Completed' result). Actual score was 4-6, 6-3, 7-6(7-2)."
        ),
        source_url="https://hr.tennistemple.com/match/lapentti-lareau-memphis-2001/407434/",
        match=lambda df: (
            (df["ATP"] == 13)
            & (df["Winner"] == "Lareau S.")
            & (df["Loser"] == "Lapentti N.")
            & (df["Date"] == "2001-02-19")
        ),
        apply=_fix_memphis_r2_2001,
    ),
    MatchFix(
        tour="atp",
        year=2006,
        description=(
            "Paris Masters final (Davydenko d. Hrbaty): Date recorded as "
            "2005-11-05, a year off from the rest of that draw (semifinals were "
            "2006-11-04); should be 2006-11-05."
        ),
        source_url="https://en.wikipedia.org/wiki/2006_Paris_Masters",
        match=lambda df: (
            (df["ATP"] == 66)
            & (df["Winner"] == "Davydenko N.")
            & (df["Loser"] == "Hrbaty D.")
            & (df["Date"] == "2005-11-05")
        ),
        apply=_fix_paris_final_2006,
    ),
    MatchFix(
        tour="atp",
        year=2007,
        description=(
            "French Open 1st Round (Monaco d. Fognini): Wsets recorded as 2 despite "
            "the full 5-set score (3-6, 2-6, 6-1, 6-2, 6-4) showing Monaco won 3 sets."
        ),
        source_url=None,
        match=lambda df: (
            (df["ATP"] == 31)
            & (df["Winner"] == "Monaco J.")
            & (df["Loser"] == "Fognini F.")
            & (df["Date"] == "2007-05-29")
        ),
        apply=_fix_french_open_r1_2007,
    ),
    MatchFix(
        tour="atp",
        year=2009,
        description=(
            "Swedish Open final (Soderling d. Monaco): all set scores missing from "
            "the raw source despite a 'Completed' straight-sets result (Wsets=2, "
            "Lsets=0). Actual score was 6-3, 7-6(7-4)."
        ),
        source_url="https://en.wikipedia.org/wiki/2009_Swedish_Open",
        match=lambda df: (
            (df["ATP"] == 38)
            & (df["Winner"] == "Soderling R.")
            & (df["Loser"] == "Monaco J.")
            & (df["Date"] == "2009-07-19")
        ),
        apply=_fix_bastad_final_2009,
    ),
    MatchFix(
        tour="atp",
        year=2006,
        description=(
            "Gstaad (Allianz Suisse Open) final (Gasquet d. Lopez): all set scores "
            "missing from the raw source. Actual score was 7-6(7-4), 6-7(3-7), 6-3, "
            "6-3 - a genuine 4-set, best-of-5 final despite this being a regular "
            "International Series event (not a Masters Series or Grand Slam)."
        ),
        source_url="https://en.wikipedia.org/wiki/2006_Allianz_Suisse_Open_Gstaad",
        match=lambda df: (
            (df["ATP"] == 38)
            & (df["Winner"] == "Gasquet R.")
            & (df["Loser"] == "Lopez F.")
            & (df["Date"] == "2006-07-15")
        ),
        apply=_fix_gstaad_final_2006,
    ),
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


def fix_atp_category_typos(df: pd.DataFrame) -> pd.DataFrame:
    """Fix known ATP raw-data entry errors found across the historical CSVs.

    | Field   | Bad value | Fix       | Occurrences                                  |
    |---------|-----------|-----------|-----------------------------------------------|
    | Comment | Sched     | Completed | 1, 2019 (US Open final, full score present)   |
    | Comment | Rrtired   | Retired   | 1, 2021 (Astana Open, retired after one set)  |

    Must run before `Comment` is cast to `category` dtype, since assigning a
    value that isn't an existing category raises.
    """
    df = df.copy()

    df.loc[df["Comment"] == "Sched", "Comment"] = "Completed"
    df.loc[df["Comment"] == "Rrtired", "Comment"] = "Retired"

    return df
