"""Stage: build/update the WTA official-tournaments table (api.wtatennis.com).

Downloads one or more seasons' tournament entries via
`datasources.wta.WtaApiClient` (paginated, 100 entries/page - server-enforced,
see `WtaApiConfig.page_size`), derives a clean one-row-per-tournament table
(`handler.wta_api.tournaments.build_wta_api_tournament_table`), and upserts
the result into a shared CSV keyed on tour/year/official_tournament_id.

Unlike the Sackmann-derived crosswalk, `official_tournament_id` here comes
straight from the WTA's own permanent `tournamentGroup.id` - no per-row
extraction/backfill needed - so this is the most authoritative id source for
the cross-source tournament mapping system (see `mapper.tournaments`).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ...config import settings
from ...datasources.wta import WtaApiClient
from ...handler.wta_api.tournaments import (
    CLEAN_TOURNAMENT_KEY_COLUMNS,
    build_wta_api_tournament_table,
)
from .._csv_upsert import upsert_csv

logger = logging.getLogger(__name__)


def tournament_table_path(clean_dir: Path | None = None) -> Path:
    """Path for the shared WTA-tournaments-API tournament-summary CSV."""
    wta_api_settings = settings.wta_api
    clean_dir = (
        clean_dir if clean_dir is not None else settings.paths.clean / wta_api_settings.clean_dir_name
    )
    return clean_dir / wta_api_settings.tournament_dir_name / wta_api_settings.tournament_filename


def build_wta_api_tournaments(
    years: range | list[int],
    *,
    client: WtaApiClient | None = None,
    clean_dir: Path | None = None,
) -> tuple[Path, int]:
    """Build/update the WTA-tournaments-API tournament-summary table.

    Fetches every tournament (all levels, ITF included - filter downstream if
    a subset is wanted) for each requested year, cleans/types it, and upserts
    into the shared CSV - keyed on tour/year/official_tournament_id, so
    re-running a subset of years only touches those years' rows.

    Returns (`table_path`, tournament rows now in the file).

    Raises:
        ValueError: If none of the requested years returned any tournaments.

    """
    client = client if client is not None else WtaApiClient()

    frames = []
    for year in years:
        df_year = client.get_tournaments(year)
        if df_year.empty:
            logger.warning("No tournaments returned for %d", year)
            continue
        frames.append(df_year)

    if not frames:
        raise ValueError(f"No tournaments returned for years {list(years)}")

    cleaned = build_wta_api_tournament_table(pd.concat(frames, ignore_index=True))

    table_path = tournament_table_path(clean_dir)
    combined = upsert_csv(
        table_path,
        cleaned,
        key_columns=CLEAN_TOURNAMENT_KEY_COLUMNS,
        date_columns=["start_date", "end_date"],
    )
    logger.info("Wrote %d tournament(s) to %s", len(combined), table_path)

    return table_path, len(combined)


__all__ = ["build_wta_api_tournaments", "tournament_table_path"]
