"""Known one-off and category-typo fixes for Tennis-Data UK raw WTA data.

See `known_fixes/_shared.py` for the `MatchFix` contract, and
notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for the
Wikipedia sources backing the single-match fixes below.
"""

from __future__ import annotations

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner.known_fixes._shared import MatchFix, set_values


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


def _fix_charleston_tourney_id_2018(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "WTA"] = 16


def _fix_guadalajara_r16_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser fully swapped - Rakhimova actually won the only completed set
    # 6-2 and led the second 3-0 before Azarenka retired, per Sackmann
    # (2024-2075_288); every column (rank, points, score, sets) needs to move.
    set_values(
        df,
        mask,
        {
            "Winner": "Rakhimova K.",
            "Loser": "Azarenka V.",
            "WRank": 89,
            "LRank": 19,
            "WPts": 812,
            "LPts": 2326,
            "W1": 6,
            "L1": 2,
            "W2": 3,
            "L2": 0,
            "Wsets": 1,
            "Lsets": 0,
        },
    )


def _fix_gasparyan_mislabeled_betova(df: pd.DataFrame, mask: pd.Series) -> None:
    # Loser recorded as "Betova M." - no such player exists in any season; this
    # is a recurring mislabeling of Margarita Gasparyan seen across multiple
    # tournaments/years (2023 Wimbledon, 2023 US Open, 2024 Hong Kong), always
    # confirmed against Sackmann's actual draw for that match.
    df.loc[mask, "Loser"] = "Gasparyan M."


def _fix_samson_mislabeled_as_winner_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    # Czech WC "Laura Samson" was mislabeled "Samsonova L." (the far better-known
    # Liudmila Samsonova) for her entire Prague/Merida runs - confirmed by score
    # against Sackmann's actual draws (2024-1082, 2024-2085), which have no
    # Samsonova entry at either event.
    df.loc[mask, "Winner"] = "Samson L."


def _fix_samson_mislabeled_as_loser_2024(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Loser"] = "Samson L."


def _fix_gdynia_baindl_mislabeled_kozlova_winner(df: pd.DataFrame, mask: pd.Series) -> None:
    # "Kozlova K." - a real but different player (Kateryna Kozlova) - is a
    # recurring mislabeling of Kateryna Baindl's entire Gdynia run; confirmed
    # by matching scores against Sackmann's actual Baindl matches (2021-2037).
    df.loc[mask, "Winner"] = "Baindl K."


def _fix_gdynia_baindl_mislabeled_kozlova_loser(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Loser"] = "Baindl K."


def _fix_kichenok_mislabeled_twin_2015(df: pd.DataFrame, mask: pd.Series) -> None:
    # Loser recorded as "Kichenok L." (Lyudmyla) - per Sackmann
    # (2015-W-INT-CAN-01A-2015_1) the actual opponent was her twin sister
    # Nadiya Kichenok, who has no other Quebec appearance in the archive.
    df.loc[mask, "Loser"] = "Kichenok N."


def _fix_gdynia_hruncakova_mislabeled_kuzmova_winner(df: pd.DataFrame, mask: pd.Series) -> None:
    # "Kuzmova V." - a real but different player (Viktoria Kuzmova) - is a
    # recurring mislabeling of Viktoria Hruncakova's Gdynia run; confirmed by
    # matching scores against Sackmann's actual Hruncakova matches (2021-2037).
    df.loc[mask, "Winner"] = "Hruncakova V."


def _fix_gdynia_hruncakova_mislabeled_kuzmova_loser(df: pd.DataFrame, mask: pd.Series) -> None:
    df.loc[mask, "Loser"] = "Hruncakova V."


def _fix_nottingham_f_2017_name_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Only the Winner/Loser name text is swapped - every other column (rank,
    # points, score) is already correctly tied to the real winner Vekic (per
    # Sackmann 2017-1080_300: Vekic d. Konta 2-6 7-6(3) 7-5).
    df.loc[mask, ["Winner", "Loser"]] = df.loc[mask, ["Loser", "Winner"]].to_numpy()


def _fix_nanchang_r32_2016_lu_jiajing_winner(df: pd.DataFrame, mask: pd.Series) -> None:
    # Two similarly-named Chinese players (Jia Jing Lu and Jing Jing Lu) had
    # their names/ranks cross-contaminated across this whole Nanchang R32
    # round. This winner is actually Jia Jing Lu (per Sackmann 2016-1077_284,
    # Jia Jing Lu d. Hantuchova 5-7 6-4 7-5) - the loser side (rank/points)
    # already correctly matches Hantuchova, confirming only the winner's
    # identity was mislabeled with the other Lu's rank/points (233/223).
    set_values(df, mask, {"Winner": "Lu Jia Jing", "WRank": 271, "WPts": 168})


def _fix_nanchang_r32_2016_lu_jingjing_loser(df: pd.DataFrame, mask: pd.Series) -> None:
    # Companion fix: this loser is actually Jing Jing Lu (per Sackmann
    # 2016-1077_276, Zhu d. Jing Jing Lu 6-3 2-6 6-4) - mislabeled with the
    # other Lu's rank/points (271/168).
    set_values(df, mask, {"Loser": "Lu Jing Jing", "LRank": 233, "LPts": 223})


def _fix_nanchang_r16_2016_lu_jiajing_loser(df: pd.DataFrame, mask: pd.Series) -> None:
    # Same Nanchang identity cross-contamination persisting into the R16:
    # this loser is actually Jia Jing Lu (per Sackmann 2016-1077_293,
    # Schiavone d. Jia Jing Lu 4-6 6-1 6-2), mislabeled with Jing Jing Lu's
    # rank/points (233/223) instead of her own (271/168).
    set_values(df, mask, {"Loser": "Lu Jia Jing", "LRank": 271, "LPts": 168})


def _fix_chicago1_r16_2021_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser fully swapped - per Sackmann (2021-2047_287), Vondrousova
    # won the first set 6-1 and led 1-0 in the second when Van Uytvanck
    # retired; the raw row's own score (Winner sets=0, Loser sets=1, 1-6 then
    # 0-1) already contradicts Van Uytvanck winning.
    set_values(
        df,
        mask,
        {
            "Winner": "Vondrousova M.",
            "Loser": "Van Uytvanck A.",
            "WRank": 40,
            "LRank": 58,
            "WPts": 1717,
            "LPts": 1230,
            "Wsets": 1,
            "Lsets": 0,
            "W1": 6,
            "L1": 1,
            "W2": 1,
            "L2": 0,
        },
    )


def _fix_adelaide_r16_2020_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser fully swapped - per Sackmann (2020-M056_288), Yastremska
    # won the first set 6-3 and led 2-0 in the second when Kerber retired;
    # the raw row's own score (Winner sets=0, Loser sets=1, 3-6 then 0-2)
    # already contradicts Kerber winning.
    set_values(
        df,
        mask,
        {
            "Winner": "Yastremska D.",
            "Loser": "Kerber A.",
            "WRank": 24,
            "LRank": 18,
            "WPts": 1820,
            "LPts": 2175,
            "Wsets": 1,
            "Lsets": 0,
            "W1": 6,
            "L1": 3,
            "W2": 2,
            "L2": 0,
        },
    )


def _fix_hobart_r32_2020_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser swapped - Sackmann (2020-1050_282) has Ferro d. Peterson
    # 4-4 RET (Peterson retired), not the other way around.
    set_values(
        df,
        mask,
        {
            "Winner": "Ferro F.",
            "Loser": "Peterson R.",
            "WRank": 63,
            "LRank": 44,
            "WPts": 926,
            "LPts": 1275,
        },
    )


def _fix_hobart_qf_2020_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser swapped - per Sackmann (2020-1050_294, W/O), Kudermetova
    # advanced past this walkover, not Muguruza.
    set_values(
        df,
        mask,
        {
            "Winner": "Kudermetova V.",
            "Loser": "Muguruza G.",
            "WRank": 42,
            "LRank": 34,
            "WPts": 1328,
            "LPts": 1467,
        },
    )


def _fix_bogota_r32_2023_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser fully swapped - per Sackmann (2023-894_279), Arango led
    # 7-5 3-1 when Tan retired, so Arango is the winner; the raw row's own
    # score (Winner sets=0, Loser sets=1, 5-7 then 1-3) already contradicts
    # Tan winning.
    set_values(
        df,
        mask,
        {
            "Winner": "Arango E.",
            "Loser": "Tan H.",
            "WRank": 242,
            "LRank": 216,
            "WPts": 274,
            "LPts": 308,
            "Wsets": 1,
            "Lsets": 0,
            "W1": 7,
            "L1": 5,
            "W2": 3,
            "L2": 1,
        },
    )


def _fix_dubai_r32_2022_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser fully swapped - per Sackmann (2022-718_273), Vondrousova
    # actually won, having lost the first set 2-6 but leading 3-0 in the
    # second when Collins retired.
    set_values(
        df,
        mask,
        {
            "Winner": "Vondrousova M.",
            "Loser": "Collins D.",
            "WRank": 38,
            "LRank": 11,
            "WPts": 1337,
            "LPts": 2971,
            "Wsets": 0,
            "Lsets": 1,
            "W1": 2,
            "L1": 6,
            "W2": 3,
            "L2": 0,
        },
    )


def _fix_dubai_sf_2022_swap(df: pd.DataFrame, mask: pd.Series) -> None:
    # Winner/Loser swapped - per Sackmann (2022-718_298, W/O), Kudermetova
    # advanced to (and lost) the final, so she - not Vondrousova - won this
    # walkover semifinal.
    set_values(
        df,
        mask,
        {
            "Winner": "Kudermetova V.",
            "Loser": "Vondrousova M.",
            "WRank": 31,
            "LRank": 38,
            "WPts": 1655,
            "LPts": 1337,
        },
    )


def _fix_parma_r32_2022_typo(df: pd.DataFrame, mask: pd.Series) -> None:
    # "Jani R-L." - hyphen instead of the period used everywhere else this
    # season ("Jani R.L." at Bogota, French Open, Budapest, Hamburg 2022).
    df.loc[mask, "Loser"] = "Jani R.L."


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
    MatchFix(
        tour="wta",
        year=2018,
        description=(
            "Charleston (Family Circle Cup) R16 (Cornet d. Bondarenko): tournament "
            "id recorded as 15 instead of 16, splitting the tournament's matches "
            "across two ids ('2018_16_charleston_family_circle_cup' and "
            "'2018_15_charleston_family_circle_cup')."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 15)
            & (df["Winner"] == "Cornet A.")
            & (df["Loser"] == "Bondarenko K.")
            & (df["Date"] == "2018-04-02")
        ),
        apply=_fix_charleston_tourney_id_2018,
    ),
    MatchFix(
        tour="wta",
        year=2018,
        description=(
            "Charleston (Family Circle Cup) semifinal (Goerges d. Sevastova): "
            "tournament id recorded as 15 instead of 16, splitting the "
            "tournament's matches across two ids ('2018_16_charleston_family_circle_cup' "
            "and '2018_15_charleston_family_circle_cup')."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 15)
            & (df["Winner"] == "Goerges J.")
            & (df["Loser"] == "Sevastova A.")
            & (df["Date"] == "2018-04-08")
        ),
        apply=_fix_charleston_tourney_id_2018,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Guadalajara Open 2nd Round (recorded as Azarenka d. Rakhimova): "
            "Winner/Loser fully swapped, along with everything keyed to them "
            "(rank, points, score, sets) - the raw row's own score (Winner sets=0, "
            "Loser sets=1, 2-6 then 0-3) already contradicts Azarenka winning. "
            "Confirmed against Sackmann (2024-2075_288, Rakhimova d. Azarenka "
            "6-2 3-0 RET)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Azarenka V.")
            & (df["Loser"] == "Rakhimova K.")
            & (df["Date"] == "2024-09-11")
        ),
        apply=_fix_guadalajara_r16_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            'Hong Kong Tennis Open 1st Round (Shi d. "Betova M."): no player '
            "named Betova exists in any season - rank/points (blank/blank) and "
            "the 6-4 6-2 score match Sackmann's Shi d. Margarita Gasparyan "
            "exactly (2024-1074_280)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 52)
            & (df["Winner"] == "Shi H.")
            & (df["Loser"] == "Betova M.")
            & (df["Date"] == "2024-10-28")
        ),
        apply=_fix_gasparyan_mislabeled_betova,
    ),
    MatchFix(
        tour="wta",
        year=2023,
        description=(
            'Wimbledon 1st Round (Juvan d. "Betova M."): same recurring '
            "Margarita Gasparyan mislabeling seen elsewhere - the 6-0 6-3 score "
            "matches Sackmann's Juvan d. Margarita Gasparyan exactly "
            "(2023-540_153)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 31)
            & (df["Winner"] == "Juvan K.")
            & (df["Loser"] == "Betova M.")
            & (df["Date"] == "2023-07-05")
        ),
        apply=_fix_gasparyan_mislabeled_betova,
    ),
    MatchFix(
        tour="wta",
        year=2023,
        description=(
            'US Open 1st Round (Miyazaki d. "Betova M."): same recurring '
            "Margarita Gasparyan mislabeling seen elsewhere - the 6-3 6-3 score "
            "matches Sackmann's Miyazaki d. Margarita Gasparyan exactly "
            "(2023-560_122)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Miyazaki Y.")
            & (df["Loser"] == "Betova M.")
            & (df["Date"] == "2023-08-28")
        ),
        apply=_fix_gasparyan_mislabeled_betova,
    ),
    MatchFix(
        tour="wta",
        year=2023,
        description=(
            "Copa Colsanitas (Bogota) 1st Round (recorded as Tan d. Arango): "
            "Winner/Loser fully swapped, along with everything keyed to them "
            "(rank, points, score, sets) - the raw row's own score (Winner "
            "sets=0, Loser sets=1, 5-7 then 1-3) already contradicts Tan "
            "winning. Confirmed against Sackmann (2023-894_279, Arango d. Tan "
            "7-5 3-1 RET)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 17)
            & (df["Winner"] == "Tan H.")
            & (df["Loser"] == "Arango E.")
            & (df["Date"] == "2023-04-04")
        ),
        apply=_fix_bogota_r32_2023_swap,
    ),
    MatchFix(
        tour="wta",
        year=2022,
        description=(
            "Dubai Duty Free Tennis Championships 3rd Round (recorded as "
            "Collins d. Vondrousova): Winner/Loser fully swapped, along with "
            "everything keyed to them (rank, points, score, sets) - per "
            "Sackmann (2022-718_273), Vondrousova lost the first set 2-6 but "
            "was leading 3-0 in the second when Collins retired, so "
            "Vondrousova is the winner."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 8)
            & (df["Winner"] == "Collins D.")
            & (df["Loser"] == "Vondrousova M.")
            & (df["Date"] == "2022-02-15")
        ),
        apply=_fix_dubai_r32_2022_swap,
    ),
    MatchFix(
        tour="wta",
        year=2022,
        description=(
            "Dubai Duty Free Tennis Championships semifinal (recorded as "
            "Vondrousova d. Kudermetova by walkover): Winner/Loser swapped - "
            "per Sackmann (2022-718_298, W/O) Kudermetova advanced to (and "
            "lost) the final, so she is the one who won this walkover."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 8)
            & (df["Winner"] == "Vondrousova M.")
            & (df["Loser"] == "Kudermetova V.")
            & (df["Date"] == "2022-02-18")
        ),
        apply=_fix_dubai_sf_2022_swap,
    ),
    MatchFix(
        tour="wta",
        year=2022,
        description=(
            'Parma Ladies Open 1st Round (Schmiedlova d. "Jani R-L."): '
            "hyphen typo instead of the period used everywhere else this "
            "season (Bogota, French Open, Budapest, Hamburg 2022 all use "
            '"Jani R.L.").'
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 48)
            & (df["Winner"] == "Schmiedlova A.")
            & (df["Loser"] == "Jani R-L.")
            & (df["Date"] == "2022-09-26")
        ),
        apply=_fix_parma_r32_2022_typo,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Prague Open 1st Round (recorded as Samsonova d. Wurth): the winner "
            "is Czech WC Laura Samson, mislabeled with Liudmila Samsonova's name "
            "(and her live rank/points) - Sackmann's actual Prague 2024 draw has "
            "no Samsonova entry, only Samson (2024-1082_271)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 35)
            & (df["Winner"] == "Samsonova L.")
            & (df["Loser"] == "Wurth T.")
            & (df["Date"] == "2024-07-22")
        ),
        apply=_fix_samson_mislabeled_as_winner_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Prague Open 2nd Round (recorded as Samsonova d. Siniakova): same "
            "Laura Samson/Samsonova mislabeling as her 1st round match "
            "(2024-1082_286)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 35)
            & (df["Winner"] == "Samsonova L.")
            & (df["Loser"] == "Siniakova K.")
            & (df["Date"] == "2024-07-23")
        ),
        apply=_fix_samson_mislabeled_as_winner_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Prague Open Quarterfinal (recorded as Samsonova d. Selekhmeteva): "
            "same Laura Samson/Samsonova mislabeling as her earlier rounds "
            "(2024-1082_280)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 35)
            & (df["Winner"] == "Samsonova L.")
            & (df["Loser"] == "Selekhmeteva O.")
            & (df["Date"] == "2024-07-24")
        ),
        apply=_fix_samson_mislabeled_as_winner_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Prague Open Semifinal (recorded as Frech d. Samsonova): same Laura "
            "Samson/Samsonova mislabeling, this time as the loser "
            "(2024-1082_298)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 35)
            & (df["Winner"] == "Frech M.")
            & (df["Loser"] == "Samsonova L.")
            & (df["Date"] == "2024-07-25")
        ),
        apply=_fix_samson_mislabeled_as_loser_2024,
    ),
    MatchFix(
        tour="wta",
        year=2024,
        description=(
            "Merida Open 1st Round (recorded as Ruzic d. Samsonova): same Laura "
            "Samson/Samsonova mislabeling as her Prague matches earlier in the "
            "season - Sackmann's Merida 2024 draw has Ruzic d. Samson 6-4 6-4 "
            "(2024-2085_276)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 54)
            & (df["Winner"] == "Ruzic A.")
            & (df["Loser"] == "Samsonova L.")
            & (df["Date"] == "2024-10-29")
        ),
        apply=_fix_samson_mislabeled_as_loser_2024,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) 3rd Round (recorded as Kozlova d. Volynets): "
            "the winner is Kateryna Baindl - mislabeled with fellow Ukrainian "
            "Kateryna Kozlova's name throughout her whole run - confirmed by "
            "score against Sackmann's actual Baindl d. Volynets 7-6(3) 6-2 "
            "(2021-2037_279)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Kozlova K.")
            & (df["Loser"] == "Volynets K.")
            & (df["Date"] == "2021-07-19")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) 4th Round (recorded as Kozlova d. Sasnovich): "
            "same Baindl/Kozlova mislabeling (2021-2037_290)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Kozlova K.")
            & (df["Loser"] == "Sasnovich A.")
            & (df["Date"] == "2021-07-22")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) Quarterfinal (recorded as Kozlova d. Kawa): "
            "same Baindl/Kozlova mislabeling (2021-2037_296)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Kozlova K.")
            & (df["Loser"] == "Kawa K.")
            & (df["Date"] == "2021-07-24")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) Semifinal (recorded as Zanevska d. Kozlova): "
            "same Baindl/Kozlova mislabeling, this time as the loser "
            "(2021-2037_299)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Zanevska M.")
            & (df["Loser"] == "Kozlova K.")
            & (df["Date"] == "2021-07-24")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_loser,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) 3rd Round (recorded as Kuzmova d. Gracheva): "
            "the winner is Viktoria Hruncakova - mislabeled with fellow "
            "Slovak Viktoria Kuzmova's name - confirmed by score against "
            "Sackmann's actual Hruncakova d. Gracheva 6-4 6-7(4) 7-5 "
            "(2021-2037_282). Already resolved via rank-based Pass 1 despite "
            "the wrong name; fixed here for data-quality consistency."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Kuzmova V.")
            & (df["Loser"] == "Gracheva V.")
            & (df["Date"] == "2021-07-21")
        ),
        apply=_fix_gdynia_hruncakova_mislabeled_kuzmova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Poland Open (Gdynia) 4th Round (recorded as Zanevska d. Kuzmova): "
            "same Hruncakova/Kuzmova mislabeling, this time as the loser "
            "(2021-2037_292)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 36)
            & (df["Winner"] == "Zanevska M.")
            & (df["Loser"] == "Kuzmova V.")
            & (df["Date"] == "2021-07-22")
        ),
        apply=_fix_gdynia_hruncakova_mislabeled_kuzmova_loser,
    ),
    MatchFix(
        tour="wta",
        year=2021,
        description=(
            "Chicago Women's Open 2nd Round (recorded as Van Uytvanck d. "
            "Vondrousova): Winner/Loser fully swapped, along with everything "
            "keyed to them (rank, points, score, sets) - the raw row's own "
            "score (Winner sets=0, Loser sets=1, 1-6 then 0-1) already "
            "contradicts Van Uytvanck winning. Confirmed against Sackmann "
            "(2021-2047_287, Vondrousova d. Van Uytvanck 6-1 1-0 RET)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Van Uytvanck A.")
            & (df["Loser"] == "Vondrousova M.")
            & (df["Date"] == "2021-08-25")
        ),
        apply=_fix_chicago1_r16_2021_swap,
    ),
    MatchFix(
        tour="wta",
        year=2020,
        description=(
            "Adelaide International 2nd Round (recorded as Kerber d. "
            "Yastremska): Winner/Loser fully swapped, along with everything "
            "keyed to them (rank, points, score, sets) - the raw row's own "
            "score (Winner sets=0, Loser sets=1, 3-6 then 0-2) already "
            "contradicts Kerber winning. Confirmed against Sackmann "
            "(2020-M056_288, Yastremska d. Kerber 6-3 2-0 RET)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 4)
            & (df["Winner"] == "Kerber A.")
            & (df["Loser"] == "Yastremska D.")
            & (df["Date"] == "2020-01-15")
        ),
        apply=_fix_adelaide_r16_2020_swap,
    ),
    MatchFix(
        tour="wta",
        year=2020,
        description=(
            "Hobart International 1st Round (recorded as Peterson d. Ferro): "
            "Winner/Loser swapped - Sackmann (2020-1050_282) has Ferro d. "
            "Peterson 4-4 RET (Peterson retired), not the reverse."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 5)
            & (df["Winner"] == "Peterson R.")
            & (df["Loser"] == "Ferro F.")
            & (df["Date"] == "2020-01-13")
        ),
        apply=_fix_hobart_r32_2020_swap,
    ),
    MatchFix(
        tour="wta",
        year=2020,
        description=(
            "Hobart International Quarterfinal (recorded as Muguruza d. "
            "Kudermetova by walkover): Winner/Loser swapped - per Sackmann "
            "(2020-1050_294, W/O) Kudermetova is the one who advanced past "
            "this walkover, not Muguruza."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 5)
            & (df["Winner"] == "Muguruza G.")
            & (df["Loser"] == "Kudermetova V.")
            & (df["Date"] == "2020-01-16")
        ),
        apply=_fix_hobart_qf_2020_swap,
    ),
    MatchFix(
        tour="wta",
        year=2017,
        description=(
            "Aegon Open Nottingham Final (recorded as Konta d. Vekic): only "
            "the Winner/Loser name text is swapped - every other column "
            "(rank, points, score) is already correctly tied to the real "
            "winner. Confirmed against Sackmann (2017-1080_300, Vekic d. "
            "Konta 2-6 7-6(3) 7-5) - the reported points (800/4330) match "
            "Sackmann's winner/loser points exactly."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 30)
            & (df["Winner"] == "Konta J.")
            & (df["Loser"] == "Vekic D.")
            & (df["Date"] == "2017-06-18")
        ),
        apply=_fix_nottingham_f_2017_name_swap,
    ),
    MatchFix(
        tour="wta",
        year=2017,
        description=(
            "Generali Ladies Linz 1st Round (recorded as Kuzmova d. "
            "Friedsam): same recurring Viktoria Kuzmova/Viktoria Hruncakova "
            "mislabeling seen at Gdynia 2021 - confirmed by score against "
            "Sackmann's actual Hruncakova d. Friedsam 6-2 7-5 (2017-0528_272)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 54)
            & (df["Winner"] == "Kuzmova V.")
            & (df["Loser"] == "Friedsam A.L.")
            & (df["Date"] == "2017-10-10")
        ),
        apply=_fix_gdynia_hruncakova_mislabeled_kuzmova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2016,
        description=(
            "Jiangxi Women's Tennis Open (Nanchang) R32 (recorded as Lu Jing "
            "Jing d. Hantuchova): the two similarly-named Chinese players Jia "
            "Jing Lu and Jing Jing Lu had their names/ranks cross-contaminated "
            "across this round. Confirmed against Sackmann (2016-1077_284, Jia "
            "Jing Lu d. Hantuchova 5-7 6-4 7-5) - loser rank/points already "
            "correctly match Hantuchova, only the winner side was mislabeled."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Lu Jing Jing")
            & (df["Loser"] == "Hantuchova D.")
            & (df["Date"] == "2016-08-02")
        ),
        apply=_fix_nanchang_r32_2016_lu_jiajing_winner,
    ),
    MatchFix(
        tour="wta",
        year=2016,
        description=(
            "Jiangxi Women's Tennis Open (Nanchang) R32 (recorded as Zhu d. "
            "Lu Jia Jing): companion fix to the Hantuchova match above - this "
            "loser is actually Jing Jing Lu, per Sackmann (2016-1077_276, Zhu "
            "d. Jing Jing Lu 6-3 2-6 6-4)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Zhu L.")
            & (df["Loser"] == "Lu Jia Jing")
            & (df["Date"] == "2016-08-02")
        ),
        apply=_fix_nanchang_r32_2016_lu_jingjing_loser,
    ),
    MatchFix(
        tour="wta",
        year=2016,
        description=(
            "Jiangxi Women's Tennis Open (Nanchang) R16 (recorded as "
            "Schiavone d. Lu Jing Jing): same identity cross-contamination "
            "persisting into the R16 - this loser is actually Jia Jing Lu, per "
            "Sackmann (2016-1077_293, Schiavone d. Jia Jing Lu 4-6 6-1 6-2)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 42)
            & (df["Winner"] == "Schiavone F.")
            & (df["Loser"] == "Lu Jing Jing")
            & (df["Date"] == "2016-08-03")
        ),
        apply=_fix_nanchang_r16_2016_lu_jiajing_loser,
    ),
    MatchFix(
        tour="wta",
        year=2015,
        description=(
            "Hobart International R32 (recorded as Kozlova d. Flipkens): "
            "same recurring Kateryna Kozlova/Kateryna Baindl mislabeling seen "
            "at Gdynia 2021 - confirmed by score against Sackmann's actual "
            "Baindl d. Flipkens 4-6 6-3 6-4 (2015-W-INT-AUS-01A-2015_3)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 4)
            & (df["Winner"] == "Kozlova K.")
            & (df["Loser"] == "Flipkens K.")
            & (df["Date"] == "2015-01-12")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_winner,
    ),
    MatchFix(
        tour="wta",
        year=2015,
        description=(
            "Hobart International R16 (recorded as Brengle d. Kozlova): same "
            "recurring Kozlova/Baindl mislabeling - confirmed by score against "
            "Sackmann's actual Brengle d. Baindl 6-1 7-6(8) "
            "(2015-W-INT-AUS-01A-2015_18)."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 4)
            & (df["Winner"] == "Brengle M.")
            & (df["Loser"] == "Kozlova K.")
            & (df["Date"] == "2015-01-15")
        ),
        apply=_fix_gdynia_baindl_mislabeled_kozlova_loser,
    ),
    MatchFix(
        tour="wta",
        year=2015,
        description=(
            "Coupe Banque Nationale (Quebec) R32 (recorded as Tatishvili d. "
            "Kichenok L.): the loser's initial names the wrong twin - "
            "Sackmann's only Quebec Kichenok match is Tatishvili d. Nadiya "
            "Kichenok 6-2 6-4 (2015-W-INT-CAN-01A-2015_1); Lyudmyla Kichenok "
            "does not appear in this tournament's draw at all."
        ),
        source_url=None,
        match=lambda df: (
            (df["WTA"] == 45)
            & (df["Winner"] == "Tatishvili A.")
            & (df["Loser"] == "Kichenok L.")
            & (df["Date"] == "2015-09-17")
        ),
        apply=_fix_kichenok_mislabeled_twin_2015,
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
    | Surface  | Clay           | Hard     | 30, 2023 (Warsaw/Poland Open, id 36) |

    Greenset is a hard-court surface brand name; WTA singles is always best-of-3.
    Warsaw's Poland Open (raw event id 36) moved to outdoor hard courts for the
    first time in 2023 (confirmed against
    https://en.wikipedia.org/wiki/2023_WTA_Poland_Open and Sackmann's own
    surface for the same matches) - the raw source kept recording "Clay",
    carried over from the event's clay-court history every other year
    (2007-2022).

    Must run before `Tier`/`Comment`/`Surface` are cast to `category` dtype,
    since assigning a value that isn't an existing category raises.
    """
    df = df.copy()

    tier_typo = df["Tier"].astype("string").str.fullmatch(r"WTA2[5-7]\d") & df["Tier"].ne("WTA250")
    df.loc[tier_typo.fillna(False), "Tier"] = "WTA250"

    df.loc[df["Comment"] == "Walkoer", "Comment"] = "Walkover"
    df.loc[df["Surface"] == "Greenset", "Surface"] = "Hard"
    df.loc[df["Best of"] != 3, "Best of"] = 3

    warsaw_2023 = (df["WTA"] == 36) & (df["Date"].dt.year == 2023)
    df.loc[warsaw_2023, "Surface"] = "Hard"

    return df
