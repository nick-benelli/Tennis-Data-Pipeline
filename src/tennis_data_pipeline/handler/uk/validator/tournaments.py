"""Tournament-level structural-consistency checks for Tennis-Data UK match data."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def find_uk_inconsistent_tournaments(
    df: pd.DataFrame,
    key_columns: list[str] | None = None,
    info_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find tournaments whose attributes aren't consistent across all their rows.

    Returns:
        metrics: distinct-value count per info column, one row per inconsistent key.
        affected_rows: the original df_uk rows belonging to those inconsistent keys,
            for manual review/fixing in the source data.

    """
    key_columns = key_columns or ["ATP", "Location"]
    info_cols = info_cols or ["Tournament", "Series", "Court", "Surface", "Best of"]

    nunique_per_key = df.groupby(key_columns)[info_cols].nunique()
    metrics = nunique_per_key[(nunique_per_key > 1).any(axis=1)]

    if metrics.empty:
        logger.debug("All tournament attributes are consistent.")
        return metrics, df.iloc[0:0]

    logger.warning("%d tournament(s) have inconsistent attributes.", len(metrics))

    affected_rows = df.merge(metrics.reset_index()[key_columns], on=key_columns, how="inner")

    return metrics, affected_rows


def find_uk_reused_tournament_ids(
    df: pd.DataFrame,
    id_col: str = "ATP",
    disambiguating_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Find tournament ids reused across genuinely different tournaments.

    `find_uk_inconsistent_tournaments` keys on (ATP, Location), so same-week
    collisions like Stockholm/Tokyo both being "ATP 58" get silently split
    into two clean groups and never show up there. This checks `id_col` on
    its own instead.

    Returns:
        metrics: distinct-value count of `disambiguating_cols` per id, one
            row per id used by more than one tournament.
        affected_rows: the original df_uk rows for those reused ids.

    """
    disambiguating_cols = disambiguating_cols or ["Location", "Tournament"]

    nunique_per_id = df.groupby(id_col)[disambiguating_cols].nunique()
    metrics = nunique_per_id[(nunique_per_id > 1).any(axis=1)]

    if metrics.empty:
        logger.debug("Every %s id maps to exactly one tournament.", id_col)
        return metrics, df.iloc[0:0]

    logger.warning("%d %s id(s) are reused across different tournaments.", len(metrics), id_col)

    affected_rows = df.merge(metrics.reset_index()[[id_col]], on=id_col, how="inner")

    return metrics, affected_rows
