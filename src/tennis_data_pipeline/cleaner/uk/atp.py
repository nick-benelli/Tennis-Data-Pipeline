import re
import pandas as pd
from . import atp_cols as cols

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def add_source_event_key(df : pd.DataFrame):
    df = df.copy()

    # Date format drifts across seasons (e.g. "1/1/23" vs. "2023-01-01").
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
    if "Year" not in list(df.columns):
        # Ensure the year column is added if it doesn't exist
        df["Year"] = df["Date"].dt.year

    df["source_event_key"] = (
        df["Year"].astype(str)
        + "_"
        + df["ATP"].astype(str)
        + "_"
        + df["Location"].map(slugify)
        + "_"
        + df["Tournament"].map(slugify)
    )

    return df

def normalize_key_value(series: pd.Series) -> pd.Series:
    return (
        series
        .astype("string")
        .str.lower()
        .str.strip()
        .str.replace(r"[^a-z0-9]+", "_", regex=True)
        .str.strip("_")
    )


def add_source_match_key(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    winner = normalize_key_value(df["winner_name"])
    loser = normalize_key_value(df["loser_name"])

    match_date = (
        df["match_date"]
        .dt.strftime("%Y-%m-%d")
    )

    df["source_match_key"] = (
        df["source_event_key"]
        + "_"
        + match_date
        + "_"
        + winner
        + "_"
        + loser
    )

    return df


def validate_clean_uk_atp_data(df: pd.DataFrame) -> None:
    """Raise ValueError on any data-quality issue found in cleaned UK ATP match data."""
    required_cols = {
        "uk_tournament_id", "year", "location", "tournament_name", "match_date",
        "series", "indoor_outdoor", "surface", "round", "best_of",
        "winner_name", "loser_name", "match_status",
        "source_event_key", "source_match_key",
    }
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Missing required columns: {sorted(missing_cols)}")

    unexpected_surfaces = set(df["surface"].dropna().unique()) - cols.EXPECTED_SURFACES
    if unexpected_surfaces:
        raise ValueError(f"Unexpected surfaces: {sorted(unexpected_surfaces)}")

    unexpected_courts = set(df["indoor_outdoor"].dropna().unique()) - cols.EXPECTED_COURTS
    if unexpected_courts:
        raise ValueError(f"Unexpected court values: {sorted(unexpected_courts)}")

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
        (df["year"] == match_date.dt.year + 1)
        & (match_date.dt.month == 12)
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
    df = df.rename(columns=cols.COLUMN_MAP)

    # rename_categories, not replace: these are `category` dtype and replace()
    # can't introduce values that aren't already categories.
    df["series"] = df["series"].cat.rename_categories(cols.SERIES_MAP)
    df["surface"] = df["surface"].cat.rename_categories(cols.SURFACE_MAP)
    df["indoor_outdoor"] = df["indoor_outdoor"].cat.rename_categories(cols.COURT_MAP)
    df["round"] = df["round"].cat.rename_categories(cols.ROUND_MAP)
    df["match_status"] = df["match_status"].cat.rename_categories(cols.STATUS_MAP)

    df = add_source_match_key(df)

    df["source"] = "tennis_data_uk"
    df["tour"] = "atp"
    df = df[cols.COLUMN_ORDER]

    validate_clean_uk_atp_data(df)

    return df

def summarize_uk_atp_quality(df: pd.DataFrame) -> None:
    print("Rows:", len(df))
    print("Duplicate match keys:", df["source_match_key"].duplicated().sum())

    print("\nMatch status:")
    print(df["match_status"].value_counts(dropna=False))

    print("\nMissingness:")
    missing_pct = (
        df.isna()
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )
    print(missing_pct[missing_pct > 0])

    print("\nCompleted matches with any missing odds:")
    completed = df["match_status"] == "completed"
    print(
        df.loc[completed, cols.ODDS_COLS]
        .isna()
        .any(axis=1)
        .sum()
    )


def build_uk_atp_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten UK ATP data-quality metrics into a single-row DataFrame (one row per report run)."""
    completed = df["match_status"] == "completed"

    missing_pct = df.isna().mean().mul(100)
    missing_pct = missing_pct[missing_pct > 0].add_prefix("missing_pct_")

    status_counts = df["match_status"].value_counts(dropna=False)
    status_counts.index = [f"status_count_{str(status).lower()}" for status in status_counts.index]
    year_reuslt = df["year"].iloc[0] if df["year"].nunique() == 1 else pd.NA
    metrics = {
        "year": year_reuslt,
        "rows": len(df),
        "duplicate_match_keys": df["source_match_key"].duplicated().sum(),
        **status_counts.to_dict(),
        "completed_missing_odds": df.loc[completed, cols.ODDS_COLS].isna().any(axis=1).sum(),
        **missing_pct.to_dict(),
    }

    index = [f"Metric_{year_reuslt}"]
    return pd.DataFrame([metrics], index=index)

__all__ = [
    "build_uk_atp_quality_report",
    "clean_uk_atp_data",
    "summarize_uk_atp_quality",
]
