"""High-level WTA-tournaments-API workflow: build/update the tournament-summary table.

    from tennis_data_pipeline.workflows.wta_api import build_wta_api_tournaments

    table_path, tournament_count = build_wta_api_tournaments(range(2020, 2027))

Paths default to `settings.paths.clean` joined with `wta_api.clean_dir_name`
(configure via config.yaml, or the TENNIS_DATA_PIPELINE_CLEAN_DIR env var).
"""

from __future__ import annotations

from .fetch import fetch_and_checkpoint_year, fetch_and_checkpoint_years, load_raw_year
from .tournaments import build_wta_api_tournaments, tournament_table_path

__all__ = [
    "build_wta_api_tournaments",
    "fetch_and_checkpoint_year",
    "fetch_and_checkpoint_years",
    "load_raw_year",
    "tournament_table_path",
]
