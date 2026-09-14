"""Tests for ATP orchestration. The client is mocked; nothing hits the live site."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from tennis_data_pipeline.sources.tennis_data_uk import atp
from tennis_data_pipeline.sources.tennis_data_uk.client import TennisDataUKClient, Tour


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ATP": 1,
                "Date": "2024-01-01",
                "Series": "ATP250",
                "Winner": "Player A",
                "Loser": "Player B",
                "WRank": "1",
                "LRank": "2",
                "Comment": "Completed",
            }
        ]
    )


def test_load_year_adds_tour_metadata() -> None:
    with patch.object(TennisDataUKClient, "load_year", return_value=_raw_frame()):
        result = atp.load_year(2024)

    assert (result["tour"] == Tour.ATP.value).all()


def test_load_year_adds_source_year_metadata() -> None:
    with patch.object(TennisDataUKClient, "load_year", return_value=_raw_frame()):
        result = atp.load_year(2024)

    assert (result["source_year"] == 2024).all()


def test_load_years_concatenates_multiple_seasons() -> None:
    with patch.object(TennisDataUKClient, "load_year", return_value=_raw_frame()):
        result = atp.load_years([2023, 2024])

    assert len(result) == 2
    assert sorted(result["source_year"].unique().tolist()) == [2023, 2024]


def test_load_years_empty_iterable_returns_empty_dataframe() -> None:
    result = atp.load_years([])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_range_invalid_bounds_raises() -> None:
    with pytest.raises(ValueError):
        atp.load_range(2024, 2020)


def test_load_range_loads_inclusive_years() -> None:
    with patch.object(TennisDataUKClient, "load_year", return_value=_raw_frame()) as mock_load:
        result = atp.load_range(2023, 2024)

    assert mock_load.call_count == 2
    assert sorted(result["source_year"].unique().tolist()) == [2023, 2024]
