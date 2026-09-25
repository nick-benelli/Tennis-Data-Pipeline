"""Formalized per-year match-linkage output settings (data/linked/{tour}/{year}/)."""

from __future__ import annotations

from .base import StrictModel


class LinkedConfig(StrictModel):
    """Filenames for the formalized per-year linkage outputs (see `mapper.matches.uk_sackmann.outputs`)."""  # noqa: E501

    review_dir_name: str = "review"
    match_links_filename_template: str = "{tour}_match_links_{year}.csv"
    enriched_matches_filename_template: str = "{tour}_matches_enriched_{year}.csv"
    linkage_summary_filename_template: str = "{tour}_linkage_summary_{year}.csv"
    linkage_ambiguous_filename_template: str = "{tour}_linkage_ambiguous_{year}.csv"
    linkage_unmatched_filename_template: str = "{tour}_linkage_unmatched_{year}.csv"
    # All-years rollup (one row per year, upserted after each per-year run) - see
    # loader.linked.all_years_summary_path / workflows.mapper.matches.uk_sackmann.
    all_years_summary_filename_template: str = "{tour}_linkage_summary.csv"
