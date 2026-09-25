"""Locate the formalized per-year UK<->Sackmann linkage outputs (data/linked/{tour}/{year}/).

See `mapper.matches.uk_sackmann.outputs` for how these tables are built, and
`workflows.mapper.matches.uk_sackmann` for the layer that writes them.
"""

from __future__ import annotations

from pathlib import Path

from ..config import settings


def year_output_dir(tour: str, year: int, linked_dir: Path | None = None) -> Path:
    """The `data/linked/{tour}/{year}/` directory for one tour+year's outputs."""
    tour = str(tour).lower()
    base = linked_dir if linked_dir is not None else settings.paths.linked
    return base / tour / str(year)


def match_crosswalk_path(output_dir: Path, tour: str, year: int) -> Path:
    """Path for one tour+year's compact lineage crosswalk CSV."""
    filename = settings.linked.match_links_filename_template.format(tour=str(tour).lower(), year=year)
    return output_dir / filename


def enriched_matches_path(output_dir: Path, tour: str, year: int) -> Path:
    """Path for one tour+year's analysis-ready enriched UK matches CSV."""
    filename = settings.linked.enriched_matches_filename_template.format(
        tour=str(tour).lower(), year=year
    )
    return output_dir / filename


def linkage_summary_path(output_dir: Path, tour: str, year: int) -> Path:
    """Path for one tour+year's one-row coverage/health summary CSV."""
    filename = settings.linked.linkage_summary_filename_template.format(
        tour=str(tour).lower(), year=year
    )
    return output_dir / filename


def all_years_summary_path(tour: str, linked_dir: Path | None = None) -> Path:
    """Path for one tour's all-years rollup summary CSV.

    (`data/linked/{tour}/{tour}_linkage_summary.csv`) - one row per year,
    upserted after each `build_match_links` run - see
    `workflows.mapper.matches.uk_sackmann`.
    """
    tour = str(tour).lower()
    base = linked_dir if linked_dir is not None else settings.paths.linked
    filename = settings.linked.all_years_summary_filename_template.format(tour=tour)
    return base / tour / filename


def linkage_ambiguous_path(output_dir: Path, tour: str, year: int) -> Path:
    """Path for one tour+year's final ambiguous-candidates review CSV."""
    filename = settings.linked.linkage_ambiguous_filename_template.format(
        tour=str(tour).lower(), year=year
    )
    return output_dir / settings.linked.review_dir_name / filename


def linkage_unmatched_path(output_dir: Path, tour: str, year: int) -> Path:
    """Path for one tour+year's final unmatched-rows review CSV."""
    filename = settings.linked.linkage_unmatched_filename_template.format(
        tour=str(tour).lower(), year=year
    )
    return output_dir / settings.linked.review_dir_name / filename


__all__ = [
    "all_years_summary_path",
    "enriched_matches_path",
    "linkage_ambiguous_path",
    "linkage_summary_path",
    "linkage_unmatched_path",
    "match_crosswalk_path",
    "year_output_dir",
]
