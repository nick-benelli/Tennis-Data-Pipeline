import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import common
from tennis_data_pipeline.handler.uk.cleaner import quality
from tennis_data_pipeline.handler.uk.cleaner import wta_cols as cols


def add_source_event_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_event_key(df, id_column="WTA")


def assign_round_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw 'Nth Round' labels to bracket codes (R16/R32/...) per tournament.

    See common.assign_round_codes() for the counting-backward-from-QF logic.
    """
    return common.assign_round_codes(df, cols.ROUND_MAP)


def normalize_key_value(series: pd.Series) -> pd.Series:
    return common.normalize_key_value(series)


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    return common.add_source_match_key(df)


def validate_clean_uk_wta_data(df: pd.DataFrame) -> None:
    """Raise ValueError on any data-quality issue found in cleaned UK WTA match data."""
    required_cols = {
        "uk_tournament_id", "year", "location", "tournament_name", "match_date",
        "series", "is_outdoor", "surface", "round", "best_of",
        "winner_name", "loser_name", "match_status",
        "source_event_key", "source_match_key",
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

    # Early-season tournaments (e.g. Brisbane, Auckland, Adelaide) often play their
    # first round in late December of the prior calendar year; treat any December
    # date in the prior year as valid for the season.
    match_date = df["match_date"]
    valid_year = (df["year"] == match_date.dt.year) | (
        (df["year"] == match_date.dt.year + 1)
        & (match_date.dt.month == 12)
    )
    invalid_year = ~valid_year
    if invalid_year.any():
        raise ValueError(f"{invalid_year.sum()} rows have year != match_date year.")

    same_player = df["winner_name"] == df["loser_name"]
    if same_player.any():
        raise ValueError(f"{same_player.sum()} rows have identical winner and loser.")

    # WTA singles is always best-of-3 (fix_wta_category_typos corrects the one
    # known bad "Best of == 5" row before this runs).
    invalid_best_of = df["best_of"] != 3
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

    df = add_source_match_key(df)

    df["source"] = "tennis_data_uk"
    df["tour"] = "wta"
    df = common.ensure_columns(df, cols.ODDS_COLS)
    # WTA singles is always best-of-3; keep set_4/set_5 as all-NaN so ATP and
    # WTA share the exact same column set.
    df = common.ensure_columns(df, [
        "winner_set_4_games", "loser_set_4_games",
        "winner_set_5_games", "loser_set_5_games",
    ])
    df = df[cols.COLUMN_ORDER]

    validate_clean_uk_wta_data(df)

    return df


def summarize_uk_wta_quality(df: pd.DataFrame) -> None:
    quality.summarize_uk_quality(df)


def build_uk_wta_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten UK WTA data-quality metrics into a single-row DataFrame (one row per report run)."""
    return quality.build_uk_quality_report(df, tour="wta")


__all__ = [
    "build_uk_wta_quality_report",
    "clean_uk_wta_data",
    "summarize_uk_wta_quality",
]
