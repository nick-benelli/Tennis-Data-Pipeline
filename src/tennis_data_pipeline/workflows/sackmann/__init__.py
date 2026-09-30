"""High-level Sackmann workflows: build/update the tournament-summary table,
and load tour-level singles matches enriched with per-set score features.

    from tennis_data_pipeline.workflows.sackmann import build_sackmann_tournaments

    table_path, tournament_count, inconsistency_count = build_sackmann_tournaments(
        "atp", range(2000, 2025)
    )

Paths default to `settings.paths.clean` joined with `sackmann.clean_dir_name`
(configure via config.yaml, or the TENNIS_DATA_PIPELINE_CLEAN_DIR env var).
"""

from __future__ import annotations

from .matches import load_local_matches, load_matches
from .tournaments import (
    build_sackmann_tournaments,
    tournament_inconsistencies_path,
    tournament_table_path,
)

__all__ = [
    "build_sackmann_tournaments",
    "load_local_matches",
    "load_matches",
    "tournament_inconsistencies_path",
    "tournament_table_path",
]
