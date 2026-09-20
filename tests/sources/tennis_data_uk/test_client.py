"""Tests for TennisDataUKClient. All HTTP calls are mocked; nothing hits the live site."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from tennis_data_pipeline.datasources.tennis_data_uk.client import (
    TennisDataUKClient,
    TennisDataUKDownloadError,
    Tour,
)


def _response(status_code: int, content: bytes = b"") -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content
    return response


def test_build_url_atp() -> None:
    client = TennisDataUKClient()
    assert client.build_url(2024, Tour.ATP, extension="xlsx") == (
        f"https://www.tennis-data.co.uk/{client.path_prefix}/2024/2024.xlsx"
    )


def test_build_url_wta() -> None:
    client = TennisDataUKClient()
    assert client.build_url(2024, Tour.WTA, extension="xlsx") == (
        f"https://www.tennis-data.co.uk/{client.path_prefix}/2024w/2024.xlsx"
    )


def test_build_url_uses_custom_path_prefix() -> None:
    client = TennisDataUKClient(path_prefix="custom-id")
    assert client.build_url(2024, Tour.ATP, extension="xlsx") == (
        "https://www.tennis-data.co.uk/custom-id/2024/2024.xlsx"
    )


def test_build_url_invalid_tour_raises() -> None:
    client = TennisDataUKClient()
    with pytest.raises(ValueError):
        client.build_url(2024, "juniors")


def test_download_year_prefers_xlsx_for_recent_year() -> None:
    client = TennisDataUKClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        return _response(200, b"recent-data")

    with patch.object(client.session, "get", side_effect=side_effect):
        content = client.download_year(2024, Tour.ATP)

    assert content == b"recent-data"
    assert requested[0].endswith(".xlsx")


def test_download_year_prefers_xls_for_legacy_year() -> None:
    client = TennisDataUKClient()
    requested: list[str] = []

    def side_effect(url: str, timeout: float) -> requests.Response:
        requested.append(url)
        if url.endswith(".xls"):
            raise requests.ConnectionError("no .xls available")
        return _response(200, b"legacy-data")

    with patch.object(client.session, "get", side_effect=side_effect):
        content = client.download_year(2000, Tour.ATP)

    assert content == b"legacy-data"
    assert requested[0].endswith(".xls")
    assert requested[1].endswith(".xlsx")


def test_download_year_https_success_no_fallback() -> None:
    client = TennisDataUKClient()
    with patch.object(
        client.session, "get", return_value=_response(200, b"ok")
    ) as mock_get:
        content = client.download_year(2024, Tour.ATP)

    assert content == b"ok"
    mock_get.assert_called_once()


def test_download_year_https_failure_falls_back_to_http() -> None:
    client = TennisDataUKClient()

    def side_effect(url: str, timeout: float) -> requests.Response:
        if url.startswith("https://"):
            raise requests.ConnectionError("https unreachable")
        return _response(200, b"http-data")

    with patch.object(client.session, "get", side_effect=side_effect):
        content = client.download_year(2024, Tour.ATP)

    assert content == b"http-data"


def test_download_year_total_failure_raises_with_both_contexts() -> None:
    client = TennisDataUKClient()

    with (
        patch.object(
            client.session, "get", side_effect=requests.ConnectionError("down")
        ),
        pytest.raises(TennisDataUKDownloadError) as exc_info,
    ):
        client.download_year(2024, Tour.ATP)

    message = str(exc_info.value)
    assert "https://" in message
    assert "http://" in message


def test_download_year_skips_http_fallback_on_definitive_404() -> None:
    client = TennisDataUKClient()

    def side_effect(url: str, timeout: float) -> requests.Response:
        return _response(404)

    with (
        patch.object(client.session, "get", side_effect=side_effect) as mock_get,
        pytest.raises(TennisDataUKDownloadError),
    ):
        client.download_year(2024, Tour.ATP)

    # Only the two HTTPS extension attempts should have been made.
    assert mock_get.call_count == 2
    assert all(call.args[0].startswith("https://") for call in mock_get.call_args_list)


def test_discover_path_prefix_updates_client() -> None:
    client = TennisDataUKClient()
    html = (
        '<a href="new-id-abc123/2024/2024.xlsx">2024</a>'
        '<a href="new-id-abc123/2024w/2024.xlsx">2024</a>'
    )

    with patch.object(
        client.session, "get", return_value=_response(200, html.encode())
    ):
        prefix = client.discover_path_prefix()

    assert prefix == "new-id-abc123"
    assert client.path_prefix == "new-id-abc123"


def test_discover_path_prefix_raises_when_not_found() -> None:
    client = TennisDataUKClient()

    with (
        patch.object(
            client.session, "get", return_value=_response(200, b"<html></html>")
        ),
        pytest.raises(TennisDataUKDownloadError),
    ):
        client.discover_path_prefix()


def test_discover_path_prefix_raises_on_request_failure() -> None:
    client = TennisDataUKClient()

    with (
        patch.object(
            client.session, "get", side_effect=requests.ConnectionError("down")
        ),
        pytest.raises(TennisDataUKDownloadError),
    ):
        client.discover_path_prefix()
