"""Shared (tour-keyed) data-quality reporting for Tennis-Data UK clean output."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import common


def build_uk_quality_report(df: pd.DataFrame, tour: str) -> pd.DataFrame:
    """Flatten one tour/season's data-quality metrics into a single-row DataFrame."""
    completed = df["match_status"] == "completed"

    missing_pct = df.isna().mean().mul(100)
    missing_pct = missing_pct[missing_pct > 0].add_prefix("missing_pct_")

    status_counts = df["match_status"].value_counts(dropna=False)
    status_counts.index = [f"status_count_{str(status).lower()}" for status in status_counts.index]

    year_result = df["year"].iloc[0] if df["year"].nunique() == 1 else pd.NA

    metrics = {
        "tour": tour,
        "year": year_result,
        "rows": len(df),
        "duplicate_match_keys": df["source_match_key"].duplicated().sum(),
        **status_counts.to_dict(),
        "completed_missing_odds": df.loc[completed, common.ODDS_COLS].isna().any(axis=1).sum(),
        **missing_pct.to_dict(),
    }

    index = [f"Metric_{tour}_{year_result}"]
    return pd.DataFrame([metrics], index=index)


def update_quality_report(report_path: Path, quality_report: pd.DataFrame) -> Path:
    """Merge one tour/season's quality report into the running master report CSV.

    Keyed on (tour, year) - re-running a tour/season overwrites only its own
    row, so ATP and WTA can safely share one report file.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if report_path.exists():
        existing_report = pd.read_csv(report_path, index_col=0)
        combined_report = pd.concat([existing_report, quality_report])
        combined_report = combined_report[~combined_report.index.duplicated(keep="last")]
    else:
        combined_report = quality_report

    # Metrics where a missing value really means "zero".
    zero_fill_cols = [
        col
        for col in combined_report.columns
        if (
            col.startswith(("status_count_", "missing_pct_"))
            or col in {"duplicate_match_keys", "completed_missing_odds"}
        )
    ]
    combined_report[zero_fill_cols] = combined_report[zero_fill_cols].fillna(0)

    combined_report = combined_report.sort_values(["tour", "year"])
    combined_report = combined_report.round(4)
    combined_report.index.name = "index"

    combined_report.to_csv(report_path)
    return report_path


def summarize_uk_quality(df: pd.DataFrame) -> None:
    """Print a quick human-readable data-quality summary (rows, dupes, status, missingness)."""
    print("Rows:", len(df))
    print("Duplicate match keys:", df["source_match_key"].duplicated().sum())

    print("\nMatch status:")
    print(df["match_status"].value_counts(dropna=False))

    print("\nMissingness:")
    missing_pct = df.isna().mean().mul(100).sort_values(ascending=False)
    print(missing_pct[missing_pct > 0])

    print("\nCompleted matches with any missing odds:")
    completed = df["match_status"] == "completed"
    print(df.loc[completed, common.ODDS_COLS].isna().any(axis=1).sum())
