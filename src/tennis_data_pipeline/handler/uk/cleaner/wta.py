"""WTA-specific Tennis-Data UK cleaning: known fixes, validation, and canonical schema."""

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import common, known_fixes, quality
from tennis_data_pipeline.handler.uk.cleaner import wta_cols as cols


def load_raw_wta_csv(path: Path, year: int) -> pd.DataFrame:
    """Safely load one season's raw Tennis-Data UK WTA CSV, ready for cleaning.

    See common.load_raw_uk_csv() for what "safely" means here: parsed dates and
    proper numeric/category dtypes, still in raw (pre-COLUMN_MAP) column names.
    """
    return common.load_raw_uk_csv(
        path,
        year,
        int_cols=cols.RAW_INT_COLS,
        category_cols=cols.RAW_CATEGORY_COLS,
        float_cols=cols.RAW_FLOAT_COLS,
        pre_dtype_hook=known_fixes.fix_wta_category_typos,
    )


def add_source_event_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_event_key(df, id_column="WTA")


def assign_round_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw 'Nth Round' labels to bracket codes (R16/R32/...) per tournament.

    See common.assign_round_codes() for the counting-backward-from-QF logic.
    """
    return common.assign_round_codes(df, cols.ROUND_MAP)


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_match_key(df)


def apply_known_match_fixes(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Apply hand-verified single-match fixes registered for this year."""
    return known_fixes.apply_match_fixes(df, tour="wta", year=year, fixes=known_fixes.WTA_MATCH_FIXES)


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
    """Raise if a WTA tournament id is reused across genuinely different tournaments."""
    common.check_reused_tournament_ids(
        df,
        year,
        id_col=cols.ID_COL,
        known_exception_years=cols.KNOWN_REUSED_TOURNAMENT_ID_YEARS,
    )


def validate_clean_uk_wta_data(df: pd.DataFrame) -> None:
    """Raise ValueError on any data-quality issue found in cleaned UK WTA match data.

    WTA singles is always best-of-3 (fix_wta_category_typos corrects the one
    known bad "Best of == 5" row before this runs); see common.validate_clean_uk_data()
    for the checks shared with ATP.
    """
    common.validate_clean_uk_data(
        df,
        expected_surfaces=cols.EXPECTED_SURFACES,
        expected_rounds=cols.EXPECTED_ROUNDS,
        odds_cols=cols.ODDS_COLS,
        valid_best_of={3},
    )


def clean_uk_wta_data(df: pd.DataFrame) -> pd.DataFrame:
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
    df["tour"] = "wta"
    df = common.ensure_columns(df, cols.ODDS_COLS)
    # WTA singles is always best-of-3; keep set_4/set_5 as all-NaN so ATP and
    # WTA share the exact same column set.
    df = common.ensure_columns(
        df,
        [
            "winner_set_4_games",
            "loser_set_4_games",
            "winner_set_5_games",
            "loser_set_5_games",
        ],
    )
    df = df[cols.COLUMN_ORDER]

    validate_clean_uk_wta_data(df)

    return df


def summarize_uk_wta_quality(df: pd.DataFrame) -> None:
    """Print a quick human-readable data-quality summary for cleaned UK WTA data."""
    quality.summarize_uk_quality(df)


def build_uk_wta_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten UK WTA data-quality metrics into a single-row DataFrame (one row per report run)."""
    return quality.build_uk_quality_report(df, tour="wta")


def clean_wta_season(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Run the full known-fixes + validation + clean pipeline for one already-loaded raw WTA season.

    Fixes run before the consistency checks (not after) so a fix that resolves
    a tournament-id issue actually prevents that check from failing.
    """
    df = apply_known_match_fixes(df, year)

    check_tournament_consistency(df, year)
    check_reused_tournament_ids(df, year)

    df = common.fix_bad_odds(df)

    return clean_uk_wta_data(df)


__all__ = [
    "build_uk_wta_quality_report",
    "clean_uk_wta_data",
    "clean_wta_season",
    "summarize_uk_wta_quality",
]
