"""Tests for `loader.mapper` - dtype-restoring loaders for data/mapping/tournaments/ CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.loader.mapper import (
    load_tournament_crosswalk,
    load_tournament_manual_matches,
    load_tournament_source_links,
)


def test_load_tournament_source_links_restores_int64_id(tmp_path: Path) -> None:
    """A plain CSV round-trip leaves official_tournament_id as float64; this restores Int64."""
    mapping_dir = tmp_path / "data" / "mapping"
    tournaments_dir = mapping_dir / "tournaments"
    tournaments_dir.mkdir(parents=True)
    csv_path = tournaments_dir / "atp_tournament_source_links.csv"
    csv_path.write_text(
        "official_tournament_id,year,source,source_tournament_id\n"
        "301.0,2000,sackmann,2000-301\n"
        ",2000,sackmann,2000-999\n"
    )

    df = load_tournament_source_links("atp", mapping_dir)

    assert str(df["official_tournament_id"].dtype) == "Int64"
    assert df.loc[0, "official_tournament_id"] == 301
    assert pd.isna(df.loc[1, "official_tournament_id"])


def test_load_tournament_source_links_missing_file_returns_empty_frame(tmp_path: Path) -> None:
    df = load_tournament_source_links("atp", tmp_path / "data" / "mapping")

    assert df.empty
    assert list(df.columns) == ["official_tournament_id", "year", "source", "source_tournament_id"]


def test_load_tournament_crosswalk_restores_int64_id(tmp_path: Path) -> None:
    mapping_dir = tmp_path / "data" / "mapping"
    tournaments_dir = mapping_dir / "tournaments"
    tournaments_dir.mkdir(parents=True)
    csv_path = tournaments_dir / "atp_tournament_crosswalk.csv"
    csv_path.write_text("location_key,official_tournament_id,location\nacapulco,807.0,Acapulco\n")

    df = load_tournament_crosswalk("atp", mapping_dir)

    assert str(df["official_tournament_id"].dtype) == "Int64"
    assert df.loc[0, "official_tournament_id"] == 807


def test_load_tournament_manual_matches_restores_int64_id(tmp_path: Path) -> None:
    mapping_dir = tmp_path / "data" / "mapping"
    tournaments_dir = mapping_dir / "tournaments"
    tournaments_dir.mkdir(parents=True)
    csv_path = tournaments_dir / "atp_tournament_manual_matches.csv"
    csv_path.write_text(
        "year,uk_source_event_key,sackmann_tourney_id,official_tournament_id\n2016,,2016-M001,9663.0\n"
    )

    df = load_tournament_manual_matches("atp", mapping_dir)

    assert str(df["official_tournament_id"].dtype) == "Int64"
    assert df.loc[0, "official_tournament_id"] == 9663
