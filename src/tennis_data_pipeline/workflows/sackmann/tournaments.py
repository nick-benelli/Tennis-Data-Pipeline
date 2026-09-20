"""Stage: build/update the Sackmann tournament-summary table.

Unlike the Tennis-Data UK pipeline, there's no local raw/clean checkpoint for
Sackmann match data yet - each run downloads the requested seasons live from
the archive mirror (`datasources.sackmann.atp`/`wta`), derives one row per
tournament (`handler.sackmann.tournaments.build_sackmann_tournament_table`),
and upserts the result into the tour's shared tournaments CSV.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ...config import settings
from ...datasources.sackmann import atp, wta
from ...datasources.sackmann.client import Tour
from ...handler.sackmann.tournaments import (
    CLEAN_TOURNAMENT_KEY_COLUMNS,
    build_sackmann_tournament_table,
)
from .._csv_upsert import upsert_csv

logger = logging.getLogger(__name__)

_LOADERS = {
    Tour.ATP: atp,
    Tour.WTA: wta,
}


def tournament_table_path(tour: Tour | str, clean_dir: Path | None = None) -> Path:
    """Path for one tour's shared Sackmann tournament-summary CSV."""
    tour = Tour(str(tour).lower())
    sackmann_settings = settings.sackmann

    clean_dir = (
        clean_dir if clean_dir is not None else settings.paths.clean / sackmann_settings.clean_dir_name
    )
    filename = sackmann_settings.tournament_filename_template.format(tour=tour.value)
    return clean_dir / tour.value / sackmann_settings.tournament_dir_name / filename


def tournament_inconsistencies_path(tour: Tour | str, clean_dir: Path | None = None) -> Path:
    """Path for one tour's Sackmann tournament-attribute-inconsistencies CSV."""
    tour = Tour(str(tour).lower())
    sackmann_settings = settings.sackmann

    clean_dir = (
        clean_dir if clean_dir is not None else settings.paths.clean / sackmann_settings.clean_dir_name
    )
    filename = sackmann_settings.tournament_inconsistencies_filename_template.format(tour=tour.value)
    return clean_dir / tour.value / sackmann_settings.tournament_dir_name / filename


def build_sackmann_tournaments(
    tour: Tour | str,
    years: range | list[int],
    *,
    clean_dir: Path | None = None,
) -> tuple[Path, int, int]:
    """Build/update one tour's Sackmann tournament-summary table.

    Downloads tour-level singles matches for the requested seasons
    (`datasources.sackmann.atp`/`wta`.load_years), derives one row per
    tournament, and upserts the result into the tour's shared tournaments
    CSV - keyed on tour/year/tourney_id, so re-running a subset of years only
    touches those years' rows. Tournaments whose attributes aren't consistent
    across their matches are upserted into a companion inconsistencies CSV
    instead of being silently dropped.

    Returns (`table_path`, tournament rows now in the file, inconsistency rows
    found this run).

    Raises:
        ValueError: If none of the requested years returned any matches.

    """
    tour = Tour(str(tour).lower())
    module = _LOADERS[tour]

    df = module.load_years(years)
    if df.empty:
        raise ValueError(f"No matches returned for {tour.value.upper()} in years {list(years)}")

    result = build_sackmann_tournament_table(df)

    table_path = tournament_table_path(tour, clean_dir)
    combined = upsert_csv(
        table_path,
        result.tournaments,
        key_columns=CLEAN_TOURNAMENT_KEY_COLUMNS,
        date_columns=["start_date", "end_date"],
    )
    logger.info("[%s] Wrote %d tournament(s) to %s", tour.value.upper(), len(combined), table_path)

    if not result.inconsistencies.empty:
        inconsistencies_path = tournament_inconsistencies_path(tour, clean_dir)
        upsert_csv(
            inconsistencies_path,
            result.inconsistencies.reset_index(),
            key_columns=CLEAN_TOURNAMENT_KEY_COLUMNS,
        )
        logger.warning(
            "[%s] %d tournament(s) have inconsistent attributes - see %s",
            tour.value.upper(),
            len(result.inconsistencies),
            inconsistencies_path,
        )

    return table_path, len(combined), len(result.inconsistencies)


__all__ = [
    "build_sackmann_tournaments",
    "tournament_inconsistencies_path",
    "tournament_table_path",
]
