"""Tests for the UK<->Sackmann match-linking workflow (`workflows.mapper.matches.uk_sackmann`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.loader.linked import (
    all_years_summary_path,
    linkage_summary_path,
    year_output_dir,
)
from tennis_data_pipeline.workflows.mapper.matches.uk_sackmann import (
    rebuild_all_years_summary,
    write_linkage_outputs,
)


def test_write_linkage_outputs_writes_to_correct_year_directory(tmp_path: Path) -> None:
    output_dir = year_output_dir("atp", 2025, linked_dir=tmp_path)

    write_linkage_outputs(
        output_dir=output_dir,
        year=2025,
        tour="atp",
        match_links=pd.DataFrame([{"source_match_key": "uk_1"}]),
        enriched_matches=pd.DataFrame([{"source_match_key": "uk_1", "winner_name": "Fritz T."}]),
        ambiguous=pd.DataFrame(columns=["source_match_key"]),
        unmatched=pd.DataFrame(columns=["source_match_key"]),
        summary=pd.DataFrame([{"year": 2025, "tour": "atp"}]),
    )

    assert output_dir == tmp_path / "atp" / "2025"
    assert (output_dir / "atp_match_links_2025.csv").exists()
    assert (output_dir / "atp_matches_enriched_2025.csv").exists()
    assert (output_dir / "atp_linkage_summary_2025.csv").exists()
    assert (output_dir / "review" / "atp_linkage_ambiguous_2025.csv").exists()
    assert (output_dir / "review" / "atp_linkage_unmatched_2025.csv").exists()

    crosswalk = pd.read_csv(output_dir / "atp_match_links_2025.csv")
    assert crosswalk["source_match_key"].tolist() == ["uk_1"]


def test_write_linkage_outputs_does_not_touch_other_years(tmp_path: Path) -> None:
    other_year_dir = year_output_dir("atp", 2024, linked_dir=tmp_path)
    other_year_dir.mkdir(parents=True)
    sentinel = other_year_dir / "atp_match_links_2024.csv"
    sentinel.write_text("untouched")

    output_dir = year_output_dir("atp", 2025, linked_dir=tmp_path)
    write_linkage_outputs(
        output_dir=output_dir,
        year=2025,
        tour="atp",
        match_links=pd.DataFrame(columns=["source_match_key"]),
        enriched_matches=pd.DataFrame(columns=["source_match_key"]),
        ambiguous=pd.DataFrame(columns=["source_match_key"]),
        unmatched=pd.DataFrame(columns=["source_match_key"]),
        summary=pd.DataFrame([{"year": 2025, "tour": "atp"}]),
    )

    assert sentinel.read_text() == "untouched"


def test_all_years_summary_path_builds_under_tour_dir(tmp_path: Path) -> None:
    path = all_years_summary_path("atp", tmp_path)

    assert path == tmp_path / "atp" / "atp_linkage_summary.csv"


def test_rebuild_all_years_summary_concatenates_persisted_year_files(tmp_path: Path) -> None:
    """The per-year summary files are the source of truth - the rollup is fully derived from them."""
    for year, coverage in [(2024, 99.0), (2025, 100.0)]:
        year_dir = year_output_dir("atp", year, linked_dir=tmp_path)
        year_dir.mkdir(parents=True)
        pd.DataFrame([{"year": year, "coverage_pct": coverage}]).to_csv(
            linkage_summary_path(year_dir, "atp", year), index=False
        )

    combined = rebuild_all_years_summary("atp", tmp_path)

    assert combined["year"].tolist() == [2024, 2025]
    assert combined.loc[combined["year"] == 2025, "coverage_pct"].item() == 100.0
    assert pd.read_csv(all_years_summary_path("atp", tmp_path))["year"].tolist() == [2024, 2025]


def test_rebuild_all_years_summary_reflects_a_rerun_year(tmp_path: Path) -> None:
    """Rerunning one year's per-year file changes its row the next time the rollup is rebuilt."""
    year_dir = year_output_dir("atp", 2025, linked_dir=tmp_path)
    year_dir.mkdir(parents=True)
    summary_path = linkage_summary_path(year_dir, "atp", 2025)

    pd.DataFrame([{"year": 2025, "coverage_pct": 98.0}]).to_csv(summary_path, index=False)
    rebuild_all_years_summary("atp", tmp_path)

    pd.DataFrame([{"year": 2025, "coverage_pct": 100.0}]).to_csv(summary_path, index=False)
    combined = rebuild_all_years_summary("atp", tmp_path)

    assert combined.loc[combined["year"] == 2025, "coverage_pct"].item() == 100.0


def test_rebuild_all_years_summary_empty_when_no_years_linked_yet(tmp_path: Path) -> None:
    combined = rebuild_all_years_summary("atp", tmp_path)

    assert combined.empty
