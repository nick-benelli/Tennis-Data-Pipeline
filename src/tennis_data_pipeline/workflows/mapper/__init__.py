"""High-level cross-source id mapping workflows.

    from tennis_data_pipeline.workflows.mapper import build_tournament_mapping
    from tennis_data_pipeline.workflows.mapper import build_match_links

    result = build_tournament_mapping("atp", 2025)
    match_result = build_match_links("atp", 2025)

Paths default to `settings.paths.mapping` joined with `mapping.tournament_dir_name`
(tournament id crosswalk); configure via config.yaml, or the
TENNIS_DATA_PIPELINE_MAPPING_DIR env var. `build_match_links` writes the
formalized per-year linkage outputs under `settings.paths.linked`
(`data/linked/{tour}/{year}/`; TENNIS_DATA_PIPELINE_LINKED_DIR env var).
"""

from __future__ import annotations

from .matches.uk_sackmann import (
    MatchLinkingResult,
    all_years_summary_path,
    build_match_links,
    enriched_matches_path,
    linkage_ambiguous_path,
    linkage_summary_path,
    linkage_unmatched_path,
    manual_match_links_path,
    match_crosswalk_path,
    rebuild_all_years_summary,
    write_linkage_outputs,
    year_output_dir,
)
from .tournaments import (
    TournamentMappingResult,
    build_tournament_mapping,
    crosswalk_path,
    manual_matches_path,
    source_links_path,
)

__all__ = [
    "MatchLinkingResult",
    "TournamentMappingResult",
    "all_years_summary_path",
    "build_match_links",
    "build_tournament_mapping",
    "crosswalk_path",
    "enriched_matches_path",
    "linkage_ambiguous_path",
    "linkage_summary_path",
    "linkage_unmatched_path",
    "manual_match_links_path",
    "manual_matches_path",
    "match_crosswalk_path",
    "rebuild_all_years_summary",
    "source_links_path",
    "write_linkage_outputs",
    "year_output_dir",
]
