"""Tests for the Stage-2 raw checkpoint sanity checks."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.datasources.tennis_data_uk.checkpoint import (
    RawCheckpointError,
    raw_checkpoint_path,
    write_raw_checkpoint,
)
from tennis_data_pipeline.datasources.tennis_data_uk.client import Tour


def test_raw_checkpoint_path_convention(tmp_path: Path) -> None:
    path = raw_checkpoint_path(Tour.ATP, 2024, raw_dir=tmp_path)
    assert path == tmp_path / "atp/atp_singles_results_2024.csv"


def test_raw_checkpoint_path_defaults_to_settings_paths_raw() -> None:
    path = raw_checkpoint_path(Tour.ATP, 2024)
    assert path == settings.paths.raw / "uk/atp/atp_singles_results_2024.csv"


def test_write_raw_checkpoint_rejects_wrong_tour_column(tmp_path: Path) -> None:
    """The real bug this guards against: a WTA download that's actually ATP data."""
    df = pd.DataFrame({"ATP": [1], "Winner": ["Player A."]})

    with pytest.raises(RawCheckpointError, match="WTA"):
        write_raw_checkpoint(df, Tour.WTA, 2024, raw_dir=tmp_path)


def test_write_raw_checkpoint_rejects_missing_tour_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"Winner": ["Player A."]})

    with pytest.raises(RawCheckpointError):
        write_raw_checkpoint(df, Tour.ATP, 2024, raw_dir=tmp_path)


def test_write_raw_checkpoint_succeeds_with_correct_tour_column(tmp_path: Path) -> None:
    df = pd.DataFrame({"ATP": [1], "Winner": ["Player A."]})

    path = write_raw_checkpoint(df, Tour.ATP, 2024, raw_dir=tmp_path)

    assert path.exists()
    assert pd.read_csv(path).equals(df)


def test_write_raw_checkpoint_warns_on_schema_drift(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    df = pd.DataFrame({"ATP": [1], "Winner": ["Player A."]})
    write_raw_checkpoint(df, Tour.ATP, 2024, raw_dir=tmp_path)

    df_with_extra_col = pd.DataFrame({"ATP": [1], "Winner": ["Player A."], "BFEW": [1.5]})

    with caplog.at_level("WARNING"):
        write_raw_checkpoint(df_with_extra_col, Tour.ATP, 2024, raw_dir=tmp_path)

    assert "schema drift" in caplog.text
    assert "BFEW" in caplog.text
