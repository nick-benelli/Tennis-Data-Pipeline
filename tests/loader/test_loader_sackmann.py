"""Tests for `loader.sackmann` - reading the Sackmann archive from a local clone."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas.testing as pdt
import pytest
import requests

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.datasources.sackmann import atp
from tennis_data_pipeline.datasources.sackmann.client import (
    SackmannClient,
    SackmannDownloadError,
    SackmannError,
)
from tennis_data_pipeline.loader import sackmann as loader_sackmann
from tennis_data_pipeline.loader.sackmann import LocalSackmannClient, load_atp_year, load_wta_year

_CSV_BODY = (
    "tourney_id,tourney_name,surface,tourney_date,match_num,winner_name,loser_name,score,best_of,round\n"
    "2024-580,Test Open,Hard,20240101,300,A,B,6-3 6-4,3,F\n"
)


def _write_archive(tmp_path: Path, tour: str, filename: str, body: str = _CSV_BODY) -> Path:
    tour_dir = tmp_path / tour
    tour_dir.mkdir(parents=True, exist_ok=True)
    path = tour_dir / filename
    path.write_text(body)
    return path


def test_load_csv_reads_file_under_tour_subdir(tmp_path: Path) -> None:
    """load_csv resolves `<local_dir>/<tour>/<filename>`, same layout as the network mirror."""
    _write_archive(tmp_path, "atp", "atp_matches_2024.csv")
    client = LocalSackmannClient(tmp_path)

    df = client.load_csv("atp", "atp_matches_2024.csv")

    assert list(df["winner_name"]) == ["A"]


def test_load_csv_missing_file_raises_download_error(tmp_path: Path) -> None:
    """A missing local file raises the same `SackmannDownloadError` the network client raises."""
    client = LocalSackmannClient(tmp_path)

    with pytest.raises(SackmannDownloadError):
        client.load_csv("atp", "atp_matches_2024.csv")


def test_local_dir_relative_path_resolves_against_project_dir(tmp_path: Path) -> None:
    """A relative `local_dir` resolves against `settings.paths.project_dir`, like `paths.*_dir`."""
    client = LocalSackmannClient("some/relative/dir")

    assert client.local_dir == settings.paths.project_dir / "some/relative/dir"


def test_local_dir_defaults_to_configured_setting(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With no argument, `local_dir` falls back to `settings.sackmann.local_dir`."""
    monkeypatch.setattr(settings.sackmann, "local_dir", str(tmp_path))

    client = LocalSackmannClient()

    assert client.local_dir == tmp_path


def test_local_dir_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """No argument and no `sackmann.local_dir` configured raises a clear `SackmannError`."""
    monkeypatch.setattr(settings.sackmann, "local_dir", None)

    with pytest.raises(SackmannError):
        LocalSackmannClient()


def test_load_atp_year_applies_the_same_cleaning_and_tagging(tmp_path: Path) -> None:
    """The wrapper delegates to `datasources.sackmann.atp.load_year`, so cleaning/tagging still apply."""
    _write_archive(tmp_path, "atp", "atp_matches_2024.csv")

    df = load_atp_year(2024, local_dir=tmp_path)

    assert (df["tour"] == "atp").all()
    assert (df["match_level"] == "main").all()
    assert (df["source_year"] == 2024).all()
    assert "canonical_match_key" in df.columns


def test_load_wta_year_reads_from_wta_subdir(tmp_path: Path) -> None:
    _write_archive(tmp_path, "wta", "wta_matches_2024.csv")

    df = load_wta_year(2024, local_dir=tmp_path)

    assert (df["tour"] == "wta").all()


def test_load_atp_year_uses_module_level_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Sanity check that `LocalSackmannClient` is what `loader.sackmann` actually instantiates."""
    _write_archive(tmp_path, "atp", "atp_matches_2024.csv")
    created: list[LocalSackmannClient] = []
    real_cls = loader_sackmann.LocalSackmannClient

    class _Spy(real_cls):  # type: ignore[misc]
        def __init__(self, local_dir: Path | str | None = None) -> None:
            super().__init__(local_dir)
            created.append(self)

    monkeypatch.setattr(loader_sackmann, "LocalSackmannClient", _Spy)

    load_atp_year(2024, local_dir=tmp_path)

    assert len(created) == 1
    assert created[0].local_dir == tmp_path


def _mocked_response(body: str) -> requests.Response:
    response = requests.Response()
    response.status_code = 200
    response._content = body.encode()
    return response


def test_local_load_matches_network_load_byte_for_byte(tmp_path: Path) -> None:
    """Same CSV content, local clone vs. network mirror, must clean/tag to an identical frame.

    `LocalSackmannClient` only overrides `load_csv` - every downstream step
    (`clean_matches`, `source_year`/`tour`/`match_type`/`match_level` tagging in
    `datasources.sackmann.atp.load_year`) is the exact same code either way, so
    the two frames should be indistinguishable.
    """
    _write_archive(tmp_path, "atp", "atp_matches_2024.csv")

    local_df = atp.load_year(2024, client=LocalSackmannClient(tmp_path))

    network_client = SackmannClient()
    with patch.object(network_client.session, "get", return_value=_mocked_response(_CSV_BODY)):
        network_df = atp.load_year(2024, client=network_client)

    pdt.assert_frame_equal(local_df, network_df)


def test_local_doubles_load_matches_network_load(tmp_path: Path) -> None:
    """Same parity check for the doubles path, which has its own `clean_doubles_matches` call."""
    doubles_body = (
        "tourney_id,tourney_name,surface,tourney_date,match_num,"
        "winner1_name,winner2_name,loser1_name,loser2_name,score,best_of,round\n"
        "2020-580,Test Open,Hard,20200101,300,A,B,C,D,6-3 6-4,3,F\n"
    )
    _write_archive(tmp_path, "atp", "atp_matches_doubles_2020.csv", doubles_body)

    local_df = atp.load_doubles_year(2020, client=LocalSackmannClient(tmp_path))

    network_client = SackmannClient()
    with patch.object(network_client.session, "get", return_value=_mocked_response(doubles_body)):
        network_df = atp.load_doubles_year(2020, client=network_client)

    pdt.assert_frame_equal(local_df, network_df)
