"""Tests for the Tennis-Data UK fetch workflow (`workflows.uk.fetch`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.datasources.tennis_data_uk.checkpoint import raw_checkpoint_path
from tennis_data_pipeline.datasources.tennis_data_uk.client import Tour
from tennis_data_pipeline.workflows.uk import fetch as fetch_module


def test_fetch_and_checkpoint_year_returns_the_raw_checkpoint_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        fetch_module,
        "fetch_and_checkpoint",
        lambda tour, year, *, client, raw_dir: pd.DataFrame({"a": [1, 2]}),
    )

    result = fetch_module.fetch_and_checkpoint_year(Tour.ATP, 2020, raw_dir=tmp_path)

    assert result == raw_checkpoint_path(Tour.ATP, 2020, tmp_path)


def test_fetch_and_checkpoint_years_skips_failures_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(tour: Tour, year: int, *, client: object, raw_dir: Path | None) -> Path:
        if year == 2021:
            raise RuntimeError("boom")
        return raw_checkpoint_path(tour, year, raw_dir)

    monkeypatch.setattr(fetch_module, "fetch_and_checkpoint_year", fake)

    written = fetch_module.fetch_and_checkpoint_years(Tour.ATP, [2020, 2021, 2022], raw_dir=tmp_path)

    assert written == [
        raw_checkpoint_path(Tour.ATP, 2020, tmp_path),
        raw_checkpoint_path(Tour.ATP, 2022, tmp_path),
    ]


def test_fetch_and_checkpoint_years_reraises_when_fail_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(tour: Tour, year: int, *, client: object, raw_dir: Path | None) -> Path:
        raise RuntimeError("boom")

    monkeypatch.setattr(fetch_module, "fetch_and_checkpoint_year", fake)

    with pytest.raises(RuntimeError, match="boom"):
        fetch_module.fetch_and_checkpoint_years(Tour.ATP, [2020], raw_dir=tmp_path, fail_fast=True)


def test_load_raw_year_dispatches_to_the_atp_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(
        fetch_module.atp,
        "load_raw_atp_csv",
        lambda path, year: calls.append((path, year)) or pd.DataFrame({"marker": ["atp"]}),
    )

    result = fetch_module.load_raw_year(Tour.ATP, 2020, raw_dir=tmp_path)

    assert result["marker"].tolist() == ["atp"]
    assert calls == [(raw_checkpoint_path(Tour.ATP, 2020, tmp_path), 2020)]


def test_load_raw_year_dispatches_to_the_wta_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(
        fetch_module.wta,
        "load_raw_wta_csv",
        lambda path, year: calls.append((path, year)) or pd.DataFrame({"marker": ["wta"]}),
    )

    result = fetch_module.load_raw_year(Tour.WTA, 2020, raw_dir=tmp_path)

    assert result["marker"].tolist() == ["wta"]
    assert calls == [(raw_checkpoint_path(Tour.WTA, 2020, tmp_path), 2020)]
