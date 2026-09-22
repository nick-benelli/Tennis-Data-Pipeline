"""High-level cross-source tournament id mapping workflow.

    from tennis_data_pipeline.workflows.mapper import build_tournament_mapping

    result = build_tournament_mapping("atp", 2025)

Paths default to `settings.paths.mapping` joined with `mapping.tournament_dir_name`
(configure via config.yaml, or the TENNIS_DATA_PIPELINE_MAPPING_DIR env var).
"""

from __future__ import annotations

from .tournaments import (
    TournamentMappingResult,
    build_tournament_mapping,
    crosswalk_path,
    manual_matches_path,
    source_links_path,
)

__all__ = [
    "TournamentMappingResult",
    "build_tournament_mapping",
    "crosswalk_path",
    "manual_matches_path",
    "source_links_path",
]
