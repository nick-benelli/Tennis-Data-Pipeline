from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import atp_cols as cols
from tennis_data_pipeline.handler.uk.cleaner import common
from tennis_data_pipeline.handler.uk.cleaner import known_fixes
from tennis_data_pipeline.handler.uk.cleaner import quality

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


def normalize_key_value(series: pd.Series) -> pd.Series:
    return common.normalize_key_value(series)


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_match_key(df)


def apply_known_best_of_fixes(df: pd.DataFrame) -> pd.DataFrame:
    """Correct raw 'Best of' values the source mislabels or omits entirely."""
    df = df.copy()

    # All ATP Grand Slams are best-of-5; the raw source mislabels some individual matches.
    grand_slam_mask = df["Tournament"].isin(ATP_BEST_OF_5_TOURNAMENTS)
    df.loc[grand_slam_mask, "Best of"] = 5

    # ATP Finals (Masters Cup) is best-of-3 for every round; the raw source omits
    # "Best of" entirely for these rows rather than mislabeling it.
    masters_cup_mask = df["Series"] == "Masters Cup"
    df.loc[masters_cup_mask & df["Best of"].isna(), "Best of"] = 3

    return df


def apply_known_match_fixes(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Apply hand-verified single-match fixes registered for this year.

    See notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for
    the Wikipedia sources backing each of these; the fixes themselves live in
    `known_fixes.py`.
    """
    return known_fixes.apply_match_fixes(
        df, tour="atp", year=year, fixes=known_fixes.ATP_MATCH_FIXES
    )


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
    """Raise ValueError on any data-quality issue found in cleaned UK ATP match data."""
    required_cols = {
        "uk_tournament_id",
        "year",
        "location",
        "tournament_name",
        "match_date",
        "series",
        "is_outdoor",
        "surface",
        "round",
        "best_of",
        "winner_name",
        "loser_name",
        "match_status",
        "source_event_key",
        "source_match_key",
    }
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    unexpected_surfaces = set(df["surface"].dropna().unique()) - cols.EXPECTED_SURFACES
    if unexpected_surfaces:
        raise ValueError(f"Unexpected surfaces: {sorted(unexpected_surfaces)}")

    unexpected_rounds = set(df["round"].dropna().unique()) - cols.EXPECTED_ROUNDS
    if unexpected_rounds:
        raise ValueError(f"Unexpected rounds: {sorted(unexpected_rounds)}")

    if df["source_match_key"].duplicated().any():
        raise ValueError("Duplicate source_match_key values found.")

    # Early-season tournaments (e.g. Brisbane, Doha, Pune) often play their first
    # Early-season tournaments (e.g. Brisbane, Doha, Chennai, Pune) often play their
    # first round in late December of the prior calendar year (the exact date varies
    # by year, e.g. Dec 30 in 2013, Dec 31 in 2018); treat any December date in the
    # prior year as valid for the season.
    match_date = df["match_date"]
    valid_year = (df["year"] == match_date.dt.year) | (
        (df["year"] == match_date.dt.year + 1) & (match_date.dt.month == 12)
    )
    invalid_year = ~valid_year
    if invalid_year.any():
        raise ValueError(f"{invalid_year.sum()} rows have year != match_date year.")

    same_player = df["winner_name"] == df["loser_name"]
    if same_player.any():
        raise ValueError(f"{same_player.sum()} rows have identical winner and loser.")

    invalid_best_of = ~df["best_of"].isin([3, 5])
    if invalid_best_of.any():
        missing_best_of = df.loc[invalid_best_of, "best_of"].isna().sum()
        unexpected_values = sorted(df.loc[invalid_best_of, "best_of"].dropna().unique())
        raise ValueError(
            f"{invalid_best_of.sum()} rows have an unexpected best_of "
            f"({missing_best_of} missing, unexpected values: {unexpected_values})."
        )

    completed = df["match_status"] == "completed"

    completed_missing_first_set = completed & (
        df["winner_set_1_games"].isna() | df["loser_set_1_games"].isna()
    )
    if completed_missing_first_set.any():
        raise ValueError(
            f"{completed_missing_first_set.sum()} completed matches "
            "are missing first-set scores."
        )

    invalid_completed_sets = (
        completed
        & df["winner_sets"].notna()
        & df["loser_sets"].notna()
        & (df["winner_sets"] <= df["loser_sets"])
    )
    if invalid_completed_sets.any():
        raise ValueError(
            f"{invalid_completed_sets.sum()} completed matches "
            "have winner_sets <= loser_sets."
        )

    for col in cols.ODDS_COLS:
        invalid_odds = df[col].notna() & (df[col] < 1)
        if invalid_odds.any():
            raise ValueError(f"{col} contains {invalid_odds.sum()} odds < 1.")


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

    df = add_source_match_key(df)

    df["source"] = "tennis_data_uk"
    df["tour"] = "atp"
    df = common.ensure_odds_columns(df, cols.ODDS_COLS)
    df = df[cols.COLUMN_ORDER]

    validate_clean_uk_atp_data(df)

    return df


def summarize_uk_atp_quality(df: pd.DataFrame) -> None:
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
