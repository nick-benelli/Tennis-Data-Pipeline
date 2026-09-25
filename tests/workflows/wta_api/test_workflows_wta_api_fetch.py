"""Tests for the WTA-tournaments-API fetch workflow (`workflows.wta_api.fetch`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.datasources.wta.checkpoint import raw_checkpoint_path
from tennis_data_pipeline.workflows.wta_api import fetch as fetch_module


def test_fetch_and_checkpoint_year_returns_the_raw_checkpoint_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        fetch_module, "fetch_and_checkpoint", lambda year, *, client, raw_dir: pd.DataFrame({"a": [1]})
    )

    result = fetch_module.fetch_and_checkpoint_year(2020, raw_dir=tmp_path)

    assert result == raw_checkpoint_path(2020, tmp_path)


def test_fetch_and_checkpoint_years_skips_failures_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(year: int, *, client: object, raw_dir: Path | None) -> Path:
        if year == 2021:
            raise RuntimeError("boom")
        return raw_checkpoint_path(year, raw_dir)

    monkeypatch.setattr(fetch_module, "fetch_and_checkpoint_year", fake)

    written = fetch_module.fetch_and_checkpoint_years([2020, 2021, 2022], raw_dir=tmp_path)

    assert written == [
        raw_checkpoint_path(2020, tmp_path),
        raw_checkpoint_path(2022, tmp_path),
    ]


def test_fetch_and_checkpoint_years_reraises_when_fail_fast(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake(year: int, *, client: object, raw_dir: Path | None) -> Path:
        raise RuntimeError("boom")

    monkeypatch.setattr(fetch_module, "fetch_and_checkpoint_year", fake)

    with pytest.raises(RuntimeError, match="boom"):
        fetch_module.fetch_and_checkpoint_years([2020], raw_dir=tmp_path, fail_fast=True)


def test_load_raw_year_reads_the_checkpoint_csv_back(tmp_path: Path) -> None:
    path = raw_checkpoint_path(2020, tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"tournamentGroup.id": [123]}).to_csv(path, index=False)

    result = fetch_module.load_raw_year(2020, raw_dir=tmp_path)

    assert result["tournamentGroup.id"].tolist() == [123]
