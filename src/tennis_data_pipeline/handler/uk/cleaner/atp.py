"""ATP-specific Tennis-Data UK cleaning: known fixes, validation, and canonical schema."""

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import atp_cols as cols
from tennis_data_pipeline.handler.uk.cleaner import common, known_fixes, quality

ATP_BEST_OF_5_TOURNAMENTS = {
    "Australian Open",
    "French Open",
    "Roland Garros",
    "Wimbledon",
    "US Open",
}


def load_raw_atp_csv(path: Path, year: int) -> pd.DataFrame:
    """Safely load one season's raw Tennis-Data UK ATP CSV, ready for cleaning.

    See common.load_raw_uk_csv() for what "safely" means here: parsed dates and
    proper numeric/category dtypes, still in raw (pre-COLUMN_MAP) column names.
    """
    return common.load_raw_uk_csv(
        path,
        year,
        int_cols=cols.RAW_INT_COLS,
        category_cols=cols.RAW_CATEGORY_COLS,
        pre_dtype_hook=known_fixes.fix_atp_category_typos,
    )


def add_source_event_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_event_key(df, id_column="ATP")


def assign_round_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw 'Nth Round' labels to bracket codes (R16/R32/...) per tournament.

    Draw sizes vary a lot, so a raw "1st Round" doesn't always mean the same
    bracket size (an ATP250's 1st Round is a Round of 32; a Grand Slam's is a
    Round of 128). See common.assign_round_codes() for the counting logic.
    """
    return common.assign_round_codes(df, cols.ROUND_MAP)


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_match_key(df)


def apply_known_best_of_fixes(df: pd.DataFrame) -> pd.DataFrame:
    """Correct raw 'Best of' values the source mislabels or omits entirely."""
    df = df.copy()

    # All ATP Grand Slams are best-of-5; the raw source mislabels some individual matches.
    grand_slam_mask = df["Tournament"].isin(ATP_BEST_OF_5_TOURNAMENTS)
    df.loc[grand_slam_mask, "Best of"] = 5

    # Best-of-5 has only ever applied to Grand Slams (always) and Masters
    # Series finals (only before the 2008 season - see
    # check_tournament_consistency()/CONSISTENCY_INFO_COLS for why "Best of"
    # is allowed to vary by round within a Masters event). Every other ATP
    # match, at any level (including Masters Cup, which is best-of-3 even in
    # the final), has always been best-of-3; the raw source occasionally
    # mislabels a single match instead of following this - e.g. the 2000
    # Lisbon Masters Cup final, or a handful of ATP250/500 finals in the
    # early-2000s data.
    always_best_of_3 = ~grand_slam_mask & (df["Series"] != "Masters")
    df.loc[always_best_of_3, "Best of"] = 3

    return df


def apply_known_match_fixes(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Apply hand-verified single-match fixes registered for this year.

    See notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for
    the Wikipedia sources backing each of these; the fixes themselves live in
    `known_fixes.py`.
    """
    return known_fixes.apply_match_fixes(df, tour="atp", year=year, fixes=known_fixes.ATP_MATCH_FIXES)


def check_tournament_consistency(df: pd.DataFrame, year: int) -> None:
    """Raise if tournament metadata is inconsistent, unless `year` is a known exception."""
    common.check_tournament_consistency(
        df,
        year,
        id_col=cols.ID_COL,
        info_cols=cols.CONSISTENCY_INFO_COLS,
        known_exception_years=cols.KNOWN_TOURNAMENT_INCONSISTENCY_YEARS,
    )


def check_reused_tournament_ids(df: pd.DataFrame, year: int) -> None:
    """Raise if an ATP tournament id is reused across genuinely different tournaments."""
    common.check_reused_tournament_ids(
        df,
        year,
        id_col=cols.ID_COL,
        known_exception_years=cols.KNOWN_REUSED_TOURNAMENT_ID_YEARS,
    )


def validate_clean_uk_atp_data(df: pd.DataFrame) -> None:
    """Raise ValueError on any data-quality issue found in cleaned UK ATP match data.

    ATP allows best_of 3 or 5 (Grand Slams/pre-2008 Masters finals are best-of-5);
    see common.validate_clean_uk_data() for the checks shared with WTA.
    """
    common.validate_clean_uk_data(
        df,
        expected_surfaces=cols.EXPECTED_SURFACES,
        expected_rounds=cols.EXPECTED_ROUNDS,
        odds_cols=cols.ODDS_COLS,
        valid_best_of={3, 5},
    )


def clean_uk_atp_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw Tennis-Data UK columns/categories to canonical names and add key columns."""
    df = add_source_event_key(df)
    df = assign_round_codes(df)
    df = df.rename(columns=cols.COLUMN_MAP)

    # rename_categories, not replace: these are `category` dtype and replace()
    # can't introduce values that aren't already categories.
    df["series"] = df["series"].cat.rename_categories(cols.SERIES_MAP)
    df["surface"] = df["surface"].cat.rename_categories(cols.SURFACE_MAP)
    # Only ever Indoor/Outdoor, so map straight to a nullable bool rather than a category.
    df["is_outdoor"] = df["is_outdoor"].map(cols.COURT_MAP).astype("boolean")
    df["match_status"] = df["match_status"].cat.rename_categories(cols.STATUS_MAP)
    df = common.add_players_remaining(df)

    df = add_source_match_key(df)

    df["source"] = "tennis_data_uk"
    df["tour"] = "atp"
    # WPts/LPts don't exist at all in the raw source before 2005.
    df = common.ensure_columns(df, ["winner_rank_points", "loser_rank_points"])
    df = common.ensure_odds_columns(df, cols.ODDS_COLS)
    df = df[cols.COLUMN_ORDER]

    validate_clean_uk_atp_data(df)

    return df


def summarize_uk_atp_quality(df: pd.DataFrame) -> None:
    """Print a quick human-readable data-quality summary for cleaned UK ATP data."""
    quality.summarize_uk_quality(df)


def build_uk_atp_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten UK ATP data-quality metrics into a single-row DataFrame (one row per report run)."""
    return quality.build_uk_quality_report(df, tour="atp")


def clean_atp_season(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Run the full known-fixes + validation + clean pipeline for one already-loaded raw ATP season.

    Fixes run before the consistency checks (not after) so a fix that resolves
    a tournament-id/best-of issue actually prevents that check from failing.
    """
    df = apply_known_best_of_fixes(df)
    df = apply_known_match_fixes(df, year)

    check_tournament_consistency(df, year)
    check_reused_tournament_ids(df, year)

    df = common.fix_bad_odds(df)

    return clean_uk_atp_data(df)


__all__ = [
    "build_uk_atp_quality_report",
    "clean_atp_season",
    "clean_uk_atp_data",
    "summarize_uk_atp_quality",
]
