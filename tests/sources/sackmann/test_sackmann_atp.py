"""Tests for ATP Sackmann loaders, incl. qual/challenger and futures tiers.

All HTTP calls are mocked; nothing hits the live archive.
"""

from __future__ import annotations

from unittest.mock import patch

import requests

from tennis_data_pipeline.datasources.sackmann import atp
from tennis_data_pipeline.datasources.sackmann.client import SackmannClient

_CSV_BODY = b"winner_name,loser_name\nA,B\n"


def _response(status_code: int, content: bytes = b"") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    return response


def test_load_year_sets_main_match_level() -> None:
    """The tour-level loader tags rows with match_level='main'."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, _CSV_BODY)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = atp.load_year(2024, client=client, clean=False)

    assert requested == [f"{client.base_url}/atp/atp_matches_2024.csv"]
    assert (df["match_level"] == "main").all()
    assert (df["match_type"] == "singles").all()
    assert (df["tour"] == "atp").all()
    assert (df["source_year"] == 2024).all()


def test_load_qual_chall_year_requests_correct_filename() -> None:
    """The qual/challenger loader requests atp_matches_qual_chall_<year>.csv."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, _CSV_BODY)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = atp.load_qual_chall_year(2025, client=client, clean=False)

    assert requested == [f"{client.base_url}/atp/atp_matches_qual_chall_2025.csv"]
    assert (df["match_level"] == "qual_chall").all()


def test_load_futures_year_requests_correct_filename() -> None:
    """The futures loader requests atp_matches_futures_<year>.csv."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, _CSV_BODY)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = atp.load_futures_year(2025, client=client, clean=False)

    assert requested == [f"{client.base_url}/atp/atp_matches_futures_2025.csv"]
    assert (df["match_level"] == "futures").all()


def test_load_qual_chall_years_concatenates_seasons() -> None:
    """Multi-year qual/challenger loading concatenates one frame per year."""
    client = SackmannClient()

    with patch.object(client.session, "get", return_value=_response(200, _CSV_BODY)):
        df = atp.load_qual_chall_years([2023, 2024], client=client, clean=False)

    assert sorted(df["source_year"].unique().tolist()) == [2023, 2024]


def test_load_futures_range_rejects_inverted_range() -> None:
    """end_year earlier than start_year raises ValueError before any request is made."""
    client = SackmannClient()

    with patch.object(client.session, "get") as mock_get:
        try:
            atp.load_futures_range(2024, 2020, client=client)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")

    mock_get.assert_not_called()


def test_load_doubles_year_requests_correct_filename_and_tags_match_type() -> None:
    """The doubles loader requests atp_matches_doubles_<year>.csv and tags match_type='doubles'."""
    client = SackmannClient()
    requested: list[str] = []
    doubles_body = b"winner1_name,winner2_name,loser1_name,loser2_name\nA,B,C,D\n"

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, doubles_body)

    with patch.object(client.session, "get", side_effect=side_effect):
        df = atp.load_doubles_year(2018, client=client, clean=False)

    assert requested == [f"{client.base_url}/atp/atp_matches_doubles_2018.csv"]
    assert (df["match_type"] == "doubles").all()
    assert (df["tour"] == "atp").all()
    assert (df["source_year"] == 2018).all()
    assert "match_level" not in df.columns


def test_load_doubles_years_concatenates_seasons() -> None:
    """Multi-year doubles loading concatenates one frame per year."""
    client = SackmannClient()
    doubles_body = b"winner1_name,winner2_name,loser1_name,loser2_name\nA,B,C,D\n"

    with patch.object(client.session, "get", return_value=_response(200, doubles_body)):
        df = atp.load_doubles_years([2018, 2019], client=client, clean=False)

    assert sorted(df["source_year"].unique().tolist()) == [2018, 2019]


def test_load_doubles_range_rejects_inverted_range() -> None:
    """end_year earlier than start_year raises ValueError before any request is made."""
    client = SackmannClient()

    with patch.object(client.session, "get") as mock_get:
        try:
            atp.load_doubles_range(2018, 2015, client=client)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError")

    mock_get.assert_not_called()
