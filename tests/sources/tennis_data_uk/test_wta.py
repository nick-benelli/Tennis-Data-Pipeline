"""Tests for WTA orchestration. The client is mocked; nothing hits the live site."""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pandas as pd
import pytest

from tennis_data_pipeline.sources.tennis_data_uk import atp, wta
from tennis_data_pipeline.sources.tennis_data_uk.client import TennisDataUKClient, Tour


def _raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "WTA": 1,
                "Date": "2024-01-01",
                "Tier": "International",
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
        result = wta.load_year(2024)

    assert (result["tour"] == Tour.WTA.value).all()


def test_load_year_adds_source_year_metadata() -> None:
    with patch.object(TennisDataUKClient, "load_year", return_value=_raw_frame()):
        result = wta.load_year(2024)

    assert (result["source_year"] == 2024).all()


def test_load_years_empty_iterable_returns_empty_dataframe() -> None:
    result = wta.load_years([])
    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_load_range_invalid_bounds_raises() -> None:
    with pytest.raises(ValueError):
        wta.load_range(2024, 2020)


def test_atp_and_wta_apis_are_symmetric() -> None:
    for name in ("load_year", "load_years", "load_range"):
        atp_params = list(inspect.signature(getattr(atp, name)).parameters)
        wta_params = list(inspect.signature(getattr(wta, name)).parameters)
        assert atp_params == wta_params
