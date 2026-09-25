"""Tests for the Tennis-Data UK clean workflow (`workflows.uk.clean`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.datasources.tennis_data_uk.client import Tour
from tennis_data_pipeline.workflows.uk import clean as clean_module
from tennis_data_pipeline.workflows.uk.clean import (
    CleanYearResult,
    clean_checkpoint_path,
    clean_year,
    clean_years,
    log_clean_summary,
    quality_report_path,
)


def test_clean_checkpoint_path_uses_the_configured_filename_template(tmp_path: Path) -> None:
    expected_name = settings.tennis_data_uk.clean_filename_template.format(tour="atp", year=2020)

    assert clean_checkpoint_path(Tour.ATP, 2020, tmp_path) == tmp_path / "atp" / expected_name


def test_quality_report_path_uses_the_configured_relpath(tmp_path: Path) -> None:
    assert quality_report_path(tmp_path) == tmp_path / settings.tennis_data_uk.quality_report_relpath


def test_clean_year_writes_the_clean_csv_and_updates_the_quality_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quality_calls = []
    monkeypatch.setattr(
        clean_module.atp, "load_raw_atp_csv", lambda path, year: pd.DataFrame({"raw": [1]})
    )
    monkeypatch.setattr(
        clean_module.atp, "clean_atp_season", lambda df, year: pd.DataFrame({"col": [1, 2, 3]})
    )
    monkeypatch.setattr(clean_module.atp, "build_uk_atp_quality_report", lambda df: {"report": "atp"})
    monkeypatch.setattr(
        clean_module.quality,
        "update_quality_report",
        lambda path, report: quality_calls.append((path, report)),
    )

    result_path = clean_year(Tour.ATP, 2020, raw_dir=tmp_path, clean_dir=tmp_path)

    assert result_path == clean_checkpoint_path(Tour.ATP, 2020, tmp_path)
    assert len(pd.read_csv(result_path)) == 3
    assert quality_calls == [(quality_report_path(tmp_path), {"report": "atp"})]


def test_clean_year_dispatches_to_wta_helpers_for_the_wta_tour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        clean_module.wta, "load_raw_wta_csv", lambda path, year: pd.DataFrame({"raw": [1]})
    )
    monkeypatch.setattr(
        clean_module.wta, "clean_wta_season", lambda df, year: pd.DataFrame({"col": [1, 2]})
    )
    monkeypatch.setattr(clean_module.wta, "build_uk_wta_quality_report", lambda df: {"report": "wta"})
    monkeypatch.setattr(clean_module.quality, "update_quality_report", lambda path, report: None)

    result_path = clean_year(Tour.WTA, 2020, raw_dir=tmp_path, clean_dir=tmp_path)

    assert len(pd.read_csv(result_path)) == 2


def test_clean_years_records_failures_without_aborting_the_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake(tour: Tour, year: int, *, raw_dir: Path | None, clean_dir: Path | None) -> tuple[Path, int]:
        if year == 2021:
            raise ValueError("bad season")
        return Path(f"/fake/{year}.csv"), 10

    monkeypatch.setattr(clean_module, "_clean_and_write_year", fake)

    results = clean_years(Tour.ATP, [2020, 2021, 2022])

    assert [r.success for r in results] == [True, False, True]
    assert results[1].error == "bad season"
    assert results[0].rows == 10


def test_clean_years_reraises_when_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(tour: Tour, year: int, *, raw_dir: Path | None, clean_dir: Path | None) -> tuple[Path, int]:
        raise ValueError("bad season")

    monkeypatch.setattr(clean_module, "_clean_and_write_year", fake)

    with pytest.raises(ValueError, match="bad season"):
        clean_years(Tour.ATP, [2020], fail_fast=True)


def test_log_clean_summary_does_not_raise_for_mixed_results() -> None:
    results = [
        CleanYearResult(year=2020, success=True, rows=10),
        CleanYearResult(year=2021, success=False, error="bad season"),
    ]

    log_clean_summary(Tour.ATP, results)
