"""Tests for `loader.mapper` - match-level (data/mapping/matches/) manual-link loader."""

from __future__ import annotations

from pathlib import Path

from tennis_data_pipeline.loader.mapper import load_manual_match_links, manual_match_links_path


def test_manual_match_links_path_builds_under_matches_dir(tmp_path: Path) -> None:
    path = manual_match_links_path("atp", tmp_path / "data" / "mapping")

    assert path == tmp_path / "data" / "mapping" / "matches" / "atp_manual_links.csv"


def test_load_manual_match_links_missing_file_returns_empty_frame(tmp_path: Path) -> None:
    df = load_manual_match_links("atp", tmp_path / "data" / "mapping")

    assert df.empty
    assert list(df.columns) == ["year", "source_match_key", "canonical_match_key"]


def test_load_manual_match_links_reads_existing_file(tmp_path: Path) -> None:
    mapping_dir = tmp_path / "data" / "mapping"
    matches_dir = mapping_dir / "matches"
    matches_dir.mkdir(parents=True)
    (matches_dir / "atp_manual_links.csv").write_text(
        "year,source_match_key,canonical_match_key\n2025,uk_1,2025-520_300\n"
    )

    df = load_manual_match_links("atp", mapping_dir)

    assert df["source_match_key"].tolist() == ["uk_1"]
    assert df["canonical_match_key"].tolist() == ["2025-520_300"]
