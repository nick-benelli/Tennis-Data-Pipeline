"""Tests for shared (tour-keyed) Tennis-Data UK quality reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner import quality


def _clean_df(year: int) -> pd.DataFrame:
    odds_cols = {col: [1.5, 1.6] for col in quality.common.ODDS_COLS}
    return pd.DataFrame(
        {
            "year": [year, year],
            "match_status": ["completed", "retired"],
            "source_match_key": ["a", "b"],
            **odds_cols,
        }
    )


def test_build_uk_quality_report_keys_by_tour_and_year() -> None:
    report = quality.build_uk_quality_report(_clean_df(2024), tour="atp")
    assert report.index.tolist() == ["Metric_atp_2024"]
    assert report.loc["Metric_atp_2024", "tour"] == "atp"
    assert report.loc["Metric_atp_2024", "year"] == 2024


def test_update_quality_report_does_not_collide_across_tours(tmp_path: Path) -> None:
    report_path = tmp_path / "report.csv"

    atp_report = quality.build_uk_quality_report(_clean_df(2024), tour="atp")
    wta_report = quality.build_uk_quality_report(_clean_df(2024), tour="wta")

    quality.update_quality_report(report_path, atp_report)
    quality.update_quality_report(report_path, wta_report)

    combined = pd.read_csv(report_path, index_col=0)
    assert sorted(combined.index) == ["Metric_atp_2024", "Metric_wta_2024"]
    assert set(combined["tour"]) == {"atp", "wta"}


def test_update_quality_report_overwrites_only_its_own_tour_year(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "report.csv"

    quality.update_quality_report(
        report_path, quality.build_uk_quality_report(_clean_df(2024), tour="atp")
    )
    quality.update_quality_report(
        report_path, quality.build_uk_quality_report(_clean_df(2024), tour="wta")
    )

    # Re-running ATP 2024 with different data should not touch the WTA 2024 row.
    updated_atp = _clean_df(2024)
    updated_atp["source_match_key"] = ["a", "a"]  # now has a duplicate
    quality.update_quality_report(
        report_path, quality.build_uk_quality_report(updated_atp, tour="atp")
    )

    combined = pd.read_csv(report_path, index_col=0)
    assert len(combined) == 2
    assert combined.loc["Metric_atp_2024", "duplicate_match_keys"] == 1
    assert combined.loc["Metric_wta_2024", "duplicate_match_keys"] == 0
