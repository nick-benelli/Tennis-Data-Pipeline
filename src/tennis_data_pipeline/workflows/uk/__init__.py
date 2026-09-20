"""High-level Tennis-Data UK workflows: download/checkpoint (Stage 1-2) and clean (Stage 3-4).

This is the easy, one-call entry point for both halves of the pipeline. Split
across a few same-purpose modules (`fetch`/`clean`/`tournaments`/`update`) but
re-exported flat here, so callers never need to reach past this package:

- "go grab the data from tennis-data.co.uk and write the raw snapshot CSV"
  (`fetch_and_checkpoint_year`/`fetch_and_checkpoint_years`, in `fetch.py`).
  The actual download lives in `datasources.tennis_data_uk.client.TennisDataUKClient`;
  the actual checkpoint-writing (with the tour/schema-drift sanity checks)
  lives in `datasources.tennis_data_uk.checkpoint`.
- "load a raw checkpoint back for inspection, no cleaning" (`load_raw_year`,
  in `fetch.py`).
- "turn a raw checkpoint into the clean, canonical-schema dataset"
  (`clean_year`/`clean_years`, in `clean.py`). The known-fixes/validation/rename
  logic lives in `handler.uk.cleaner.atp`/`handler.uk.cleaner.wta`.
- "build/update the tournament-summary table" (`build_uk_tournaments`, in
  `tournaments.py`).
- "do the whole thing end to end, best-effort, safe to run unattended on a
  schedule" (`update_current_season`, in `update.py`) - see
  `scripts/uk/weekly_update.py`.

    from tennis_data_pipeline.workflows.uk import (
        fetch_and_checkpoint_years,
        clean_years,
        log_clean_summary,
    )

    fetch_and_checkpoint_years("atp", range(2020, 2025))
    results = clean_years("atp", range(2020, 2025))
    log_clean_summary("atp", results)

Paths default to `settings.paths.raw` / `settings.paths.clean`, each joined
with `tennis_data_uk.raw_dir_name` / `tennis_data_uk.clean_dir_name`
(configure via config.yaml, or the TENNIS_DATA_PIPELINE_RAW_DIR /
TENNIS_DATA_PIPELINE_CLEAN_DIR env vars).
"""

from __future__ import annotations

from .clean import (
    CleanYearResult,
    clean_checkpoint_path,
    clean_year,
    clean_years,
    log_clean_summary,
    quality_report_path,
)
from .fetch import (
    fetch_and_checkpoint_year,
    fetch_and_checkpoint_years,
    load_raw_year,
)
from .tournaments import (
    build_uk_tournaments,
    tournament_inconsistencies_path,
    tournament_table_path,
)
from .update import (
    SeasonUpdateReport,
    YearUpdateResult,
    log_season_update_report,
    update_current_season,
)

__all__ = [
    "CleanYearResult",
    "SeasonUpdateReport",
    "YearUpdateResult",
    "build_uk_tournaments",
    "clean_checkpoint_path",
    "clean_year",
    "clean_years",
    "fetch_and_checkpoint_year",
    "fetch_and_checkpoint_years",
    "load_raw_year",
    "log_clean_summary",
    "log_season_update_report",
    "quality_report_path",
    "tournament_inconsistencies_path",
    "tournament_table_path",
    "update_current_season",
]
