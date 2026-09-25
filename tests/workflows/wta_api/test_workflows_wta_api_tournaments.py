"""Tests for the WTA-tournaments-API tournaments workflow (`workflows.wta_api.tournaments`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.config import settings
from tennis_data_pipeline.workflows.wta_api import tournaments as tournaments_module
from tennis_data_pipeline.workflows.wta_api.tournaments import (
    build_wta_api_tournaments,
    tournament_table_path,
)


def test_tournament_table_path_uses_the_configured_filename(tmp_path: Path) -> None:
    wta_api_settings = settings.wta_api

    assert tournament_table_path(tmp_path) == (
        tmp_path / wta_api_settings.tournament_dir_name / wta_api_settings.tournament_filename
    )


class _FakeClient:
    def __init__(self, by_year: dict[int, pd.DataFrame]) -> None:
        self._by_year = by_year
        self.requested_years: list[int] = []

    def get_tournaments(self, year: int) -> pd.DataFrame:
        self.requested_years.append(year)
        return self._by_year.get(year, pd.DataFrame())


def test_build_wta_api_tournaments_fetches_every_requested_year(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _FakeClient({2020: pd.DataFrame({"official_tournament_id": [1]})})
    monkeypatch.setattr(
        tournaments_module,
        "build_wta_api_tournament_table",
        lambda df: pd.DataFrame({"tour": ["wta"], "year": [2020], "official_tournament_id": [1]}),
    )

    table_path, num_tournaments = build_wta_api_tournaments([2020], client=client, clean_dir=tmp_path)

    assert client.requested_years == [2020]
    assert table_path == tournament_table_path(tmp_path)
    assert num_tournaments == 1
    assert pd.read_csv(table_path).shape[0] == 1


def test_build_wta_api_tournaments_skips_years_with_no_tournaments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _FakeClient({2020: pd.DataFrame({"official_tournament_id": [1]})})
    concatenated = []
    monkeypatch.setattr(
        tournaments_module,
        "build_wta_api_tournament_table",
        lambda df: (
            concatenated.append(df)
            or pd.DataFrame({"tour": ["wta"], "year": [2020], "official_tournament_id": [1]})
        ),
    )

    build_wta_api_tournaments([2019, 2020], client=client, clean_dir=tmp_path)

    assert client.requested_years == [2019, 2020]
    assert len(concatenated[0]) == 1  # only 2020's row made it into the concatenated frame


def test_build_wta_api_tournaments_raises_when_nothing_is_returned(tmp_path: Path) -> None:
    client = _FakeClient({})

    with pytest.raises(ValueError, match="No tournaments returned"):
        build_wta_api_tournaments([2020], client=client, clean_dir=tmp_path)
