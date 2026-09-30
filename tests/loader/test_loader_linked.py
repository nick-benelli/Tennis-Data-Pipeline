"""Tests for `loader.linked` - dtype-restoring loaders for data/linked/ CSVs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tennis_data_pipeline.loader.linked import load_enriched_matches, load_match_links

_MATCH_LINKS_HEADER = (
    "year,tour,source_match_key,canonical_match_key,official_tournament_id,winner_id,loser_id,"
    "match_method,review_flag,data_quality_flag,source_candidate_count,canonical_candidate_count,"
    "round_agrees,winner_rank_points_diff,loser_rank_points_diff\n"
)
_MATCH_LINKS_ROW = (
    "2017,atp,2017_1_brisbane_..._thompson_j_ymer_e,2017-M020_276,339,111442,111200,"
    "tournament_rank_unique,False,,1,1,True,0,0\n"
)


def _write_match_links(tmp_path: Path, tour: str, year: int) -> Path:
    output_dir = tmp_path / tour / str(year)
    output_dir.mkdir(parents=True)
    path = output_dir / f"{tour}_match_links_{year}.csv"
    path.write_text(_MATCH_LINKS_HEADER + _MATCH_LINKS_ROW)
    return path


def test_load_match_links_restores_dtypes(tmp_path: Path) -> None:
    _write_match_links(tmp_path, "atp", 2017)

    df = load_match_links("atp", 2017, linked_dir=tmp_path)

    assert str(df["official_tournament_id"].dtype) == "Int64"
    assert str(df["winner_id"].dtype) == "Int64"
    assert str(df["review_flag"].dtype) == "boolean"
    assert str(df["round_agrees"].dtype) == "boolean"
    assert str(df["winner_rank_points_diff"].dtype) == "Float64"
    assert str(df["tour"].dtype) == "category"
    assert str(df["match_method"].dtype) == "category"
    assert df.loc[0, "official_tournament_id"] == 339
    assert pd.isna(df.loc[0, "data_quality_flag"])


def test_load_enriched_matches_restores_uk_and_linkage_dtypes(tmp_path: Path) -> None:
    output_dir = tmp_path / "atp" / "2017"
    output_dir.mkdir(parents=True)
    path = output_dir / "atp_matches_enriched_2017.csv"
    header = (
        "year,tour,match_date,winner_name,loser_name,winner_rank,loser_rank,"
        "canonical_match_key,official_tournament_id,canonical_tourney_id,canonical_tourney_name,"
        "canonical_round,canonical_winner_id,canonical_winner_name,canonical_loser_id,"
        "canonical_loser_name,match_method,review_flag,data_quality_flag\n"
    )
    row = (
        "2017,atp,2017-01-16,Federer R.,Melzer J.,9,102,2017-580_102,580,2017-580,"
        "Australian Open,R128,103819,Roger Federer,105589,Jurgen Melzer,"
        "tournament_rank_unique,False,\n"
    )
    path.write_text(header + row)

    df = load_enriched_matches("atp", 2017, linked_dir=tmp_path)

    assert str(df["official_tournament_id"].dtype) == "Int64"
    assert str(df["canonical_winner_id"].dtype) == "Int64"
    assert str(df["canonical_round"].dtype) == "category"
    assert str(df["match_method"].dtype) == "category"
    assert str(df["review_flag"].dtype) == "boolean"
    # UK-native columns still get loader.uk's own dtype restoration.
    assert str(df["winner_rank"].dtype) == "Int64"
    assert str(df["winner_name"].dtype) == "string"


def test_load_match_links_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_match_links("atp", 2099, linked_dir=tmp_path)
