"""Tests for WtaApiClient. All HTTP calls are mocked; nothing hits the live API."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tennis_data_pipeline.datasources.wta.client import (
    WtaApiClient,
    WtaApiDownloadError,
    flatten_tournament,
)

_TOURNAMENT_ENTRY = {
    "tournamentGroup": {"id": 609, "name": "INDIAN WELLS", "level": "WTA 1000", "metadata": {}},
    "level": "WTA 1000",
    "title": "BNP Paribas Open - Indian Wells, CA, USA",
    "year": 2025,
    "startDate": "2025-03-05",
    "endDate": "2025-03-16",
    "surface": "Hard",
    "inOutdoor": "O",
    "city": "INDIAN WELLS",
    "country": "USA",
    "singlesDrawSize": 96,
    "doublesDrawSize": 32,
    "prizeMoney": 9489532,
    "prizeMoneyCurrency": "USD",
    "status": "past",
    "winners": [
        {
            "singles": {"player": {"fullName": "Mirra Andreeva"}},
            "doubles": [],
        }
    ],
}


def test_flatten_tournament_extracts_expected_fields() -> None:
    """Flattening pulls the permanent tournament_group_id and singles champion."""
    row = flatten_tournament(_TOURNAMENT_ENTRY)

    assert row["tournament_group_id"] == 609
    assert row["group_name"] == "INDIAN WELLS"
    assert row["singles_champion"] == "Mirra Andreeva"


def test_flatten_tournament_handles_no_winners() -> None:
    """An entry with no winners (e.g. not yet played) doesn't raise."""
    entry = dict(_TOURNAMENT_ENTRY, winners=[])

    row = flatten_tournament(entry)

    assert row["singles_champion"] is None


def test_flatten_tournament_handles_doubles_only_winner() -> None:
    """A winners entry with `singles: None` (doubles-only) is skipped, not an error."""
    entry = dict(_TOURNAMENT_ENTRY, winners=[{"singles": None, "doubles": []}])

    row = flatten_tournament(entry)

    assert row["singles_champion"] is None


def test_get_tournaments_page_builds_expected_request() -> None:
    """The page request includes year-range params and respects the page arg."""
    client = WtaApiClient()
    captured: dict = {}

    def fake_get(url: str, params: dict, timeout: float, verify: bool):
        captured["url"] = url
        captured["params"] = params

        class _Response:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"pageInfo": {}, "content": [_TOURNAMENT_ENTRY]}

        return _Response()

    with patch.object(client.session, "get", side_effect=fake_get):
        payload = client.get_tournaments_page(2025, page=1)

    assert captured["params"]["page"] == 1
    assert captured["params"]["from"] == "2025-01-01"
    assert captured["params"]["to"] == "2025-12-31"
    assert payload["content"] == [_TOURNAMENT_ENTRY]


def test_iter_tournament_entries_pages_until_empty() -> None:
    """Pagination stops as soon as a page's `content` is empty."""
    client = WtaApiClient()
    pages = [
        {"pageInfo": {}, "content": [_TOURNAMENT_ENTRY]},
        {"pageInfo": {}, "content": [_TOURNAMENT_ENTRY]},
        {"pageInfo": {}, "content": []},
    ]

    with patch.object(client, "get_tournaments_page", side_effect=pages):
        entries = client.iter_tournament_entries(2025)

    assert entries == [_TOURNAMENT_ENTRY, _TOURNAMENT_ENTRY]


def test_get_tournaments_returns_flat_dataframe() -> None:
    """`get_tournaments` returns one flattened row per entry across all pages."""
    client = WtaApiClient()

    with patch.object(client, "iter_tournament_entries", return_value=[_TOURNAMENT_ENTRY]):
        df = client.get_tournaments(2025)

    assert len(df) == 1
    assert df.iloc[0]["tournament_group_id"] == 609


def test_get_tournaments_page_wraps_request_errors() -> None:
    """A network/HTTP error is wrapped in WtaApiDownloadError."""
    client = WtaApiClient()

    import requests

    with patch.object(client.session, "get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(WtaApiDownloadError):
            client.get_tournaments_page(2025)


def test_get_tournaments_page_sends_exclude_levels_as_csv() -> None:
    """A list of levels is joined into a single comma-separated query param."""
    client = WtaApiClient()
    captured: dict = {}

    def fake_get(url: str, params: dict, timeout: float, verify: bool):
        captured["params"] = params

        class _Response:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"pageInfo": {}, "content": []}

        return _Response()

    with patch.object(client.session, "get", side_effect=fake_get):
        client.get_tournaments_page(2025, exclude_levels=["ITF", "WTA 125"])

    assert captured["params"]["excludeLevels"] == "ITF,WTA 125"


def test_get_tournaments_page_omits_exclude_levels_when_not_given() -> None:
    """No `excludeLevels` param is sent unless explicitly requested."""
    client = WtaApiClient()
    captured: dict = {}

    def fake_get(url: str, params: dict, timeout: float, verify: bool):
        captured["params"] = params

        class _Response:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict:
                return {"pageInfo": {}, "content": []}

        return _Response()

    with patch.object(client.session, "get", side_effect=fake_get):
        client.get_tournaments_page(2025)

    assert "excludeLevels" not in captured["params"]
