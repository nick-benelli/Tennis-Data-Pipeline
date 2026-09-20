"""Tests for SackmannClient. All HTTP calls are mocked; nothing hits the live archive."""

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
import requests

from tennis_data_pipeline.datasources.sackmann.client import (
    SackmannClient,
    SackmannDownloadError,
    Tour,
)


def _response(status_code: int, content: bytes = b"") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    return response


def test_build_url_atp() -> None:
    """ATP URLs are built under the archive's 'atp' directory."""
    client = SackmannClient()
    assert client.build_url(Tour.ATP, "atp_matches_2024.csv") == (
        f"{client.base_url}/atp/atp_matches_2024.csv"
    )


def test_build_url_wta() -> None:
    """WTA URLs are built under the archive's 'wta' directory."""
    client = SackmannClient()
    assert client.build_url(Tour.WTA, "wta_matches_2024.csv") == (
        f"{client.base_url}/wta/wta_matches_2024.csv"
    )


def test_build_url_uses_custom_base_url() -> None:
    """An explicit base_url overrides the configured default."""
    client = SackmannClient(base_url="https://example.test/archive")
    assert client.build_url(Tour.ATP, "atp_matches_2024.csv") == (
        "https://example.test/archive/atp/atp_matches_2024.csv"
    )


def test_build_url_invalid_tour_raises() -> None:
    """An unrecognized tour string raises ValueError."""
    client = SackmannClient()
    with pytest.raises(ValueError):
        client.build_url("juniors", "whatever.csv")


def test_load_matches_uses_tour_prefixed_filename() -> None:
    """load_matches requests '<tour>_matches_<year>.csv' under the tour directory."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, b"winner_name,loser_name\nA,B\n")

    with patch.object(client.session, "get", side_effect=side_effect):
        df = client.load_matches(2024, Tour.ATP)

    assert requested == [f"{client.base_url}/atp/atp_matches_2024.csv"]
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["winner_name", "loser_name"]


def test_load_players_uses_players_filename() -> None:
    """load_players requests the tour's '<tour>_players.csv' file."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, b"player_id,name_first\n100001,Roger\n")

    with patch.object(client.session, "get", side_effect=side_effect):
        client.load_players(Tour.WTA)

    assert requested == [f"{client.base_url}/wta/wta_players.csv"]


def test_load_rankings_current_uses_rankings_filename() -> None:
    """load_rankings_current requests the tour's '<tour>_rankings_current.csv' file."""
    client = SackmannClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, b"ranking_date,rank,player\n20240101,1,100001\n")

    with patch.object(client.session, "get", side_effect=side_effect):
        client.load_rankings_current(Tour.ATP)

    assert requested == [f"{client.base_url}/atp/atp_rankings_current.csv"]


def test_load_csv_raises_on_http_error() -> None:
    """A network/HTTP failure is wrapped in SackmannDownloadError."""
    client = SackmannClient()

    with patch.object(client.session, "get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(SackmannDownloadError):
            client.load_matches(2024, Tour.ATP)
