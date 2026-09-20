"""Tests for WTA Sackmann loaders, incl. the qual/ITF tier.

All HTTP calls are mocked; nothing hits the live archive.
"""

from __future__ import annotations

from unittest.mock import patch

import requests

from tennis_data_pipeline.datasources.sackmann import wta
from tennis_data_pipeline.datasources.sackmann.client import SackmannClient

_CSV_BODY = b"winner_name,loser_name\nA,B\n"


def _response(status_code: int, content: bytes = b"") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    return response


def test_load_year_sets_main_match_level() -> None:
    """The tour-level loader tags rows with match_level='main' and match_type='singles'."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, _CSV_BODY)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = wta.load_year(2025, client=client, clean=False)

    assert requested == [f"{client.base_url}/wta/wta_matches_2025.csv"]
    assert (df["match_level"] == "main").all()
    assert (df["match_type"] == "singles").all()
    assert (df["tour"] == "wta").all()
    assert (df["source_year"] == 2025).all()


def test_load_qual_itf_year_requests_correct_filename() -> None:
    """The qual/ITF loader requests wta_matches_qual_itf_<year>.csv."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, _CSV_BODY)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = wta.load_qual_itf_year(2026, client=client, clean=False)

    assert requested == [f"{client.base_url}/wta/wta_matches_qual_itf_2026.csv"]
    assert (df["match_level"] == "qual_itf").all()
    assert (df["match_type"] == "singles").all()


def test_load_qual_itf_years_concatenates_seasons() -> None:
    """Multi-year qual/ITF loading concatenates one frame per year."""
    client = SackmannClient()

    with patch.object(client.session, "get", return_value=_response(200, _CSV_BODY)):
        df = wta.load_qual_itf_years([2024, 2025], client=client, clean=False)

    assert sorted(df["source_year"].unique().tolist()) == [2024, 2025]


def test_load_qual_itf_range_rejects_inverted_range() -> None:
    """end_year earlier than start_year raises ValueError before any request is made."""
    client = SackmannClient()

    with patch.object(client.session, "get") as mock_get:
        try:
            wta.load_qual_itf_range(2025, 2020, client=client)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")

    mock_get.assert_not_called()
