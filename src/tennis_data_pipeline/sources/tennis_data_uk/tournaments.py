"""Tournament-level summaries derived from Tennis-Data UK match data."""

from __future__ import annotations

import pandas as pd

# Attributes expected to be constant for every match within a tournament.
_ATTRIBUTE_COLUMNS = ["Tournament", "Series", "Court", "Surface", "Best of"]


def _mode_or_na(series: pd.Series) -> object:
    """Most frequent value in the group (smooths over stray data-entry errors)."""
    mode = series.mode()
    return mode.iloc[0] if not mode.empty else pd.NA


def build_tournament_table(
    df: pd.DataFrame,
    *,
    key_columns: list[str] | None = None,
    attribute_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Derive one row per tournament from match-level Tennis-Data UK data.

    Tournament number columns (``ATP``/``WTA``, or ``TournamentNumber`` after
    ``clean_matches``) are reused across seasons and, on rare weeks, across
    concurrent tournaments in the same season. ``key_columns`` must include
    enough columns to disambiguate those cases: ``source_year`` when combining
    multiple seasons, and ``Location`` to split same-week collisions within a
    season.

    Args:
        df: Match-level data containing ``Date``, ``key_columns``, and
            ``attribute_columns`` (e.g. the output of ``atp.load_year``/
            ``wta.load_year``, or a Tennis-Data UK season CSV read as-is).
        key_columns: Columns that together uniquely identify a tournament.
            Defaults to ``["source_year", "TournamentNumber", "Location"]``.
            If ``source_year`` is requested but absent, it is derived from
            ``Date``.
        attribute_columns: Columns expected to be constant within a
            tournament. Defaults to
            ``["Tournament", "Series", "Court", "Surface", "Best of"]``.

    Returns:
        A tuple of ``(tournaments, inconsistencies)``:

        - ``tournaments``: one row per tournament with the most common value
          of each attribute column, plus ``Start_Date``/``End_Date``.
        - ``inconsistencies``: per-key counts of distinct values for each
          attribute column, filtered to keys with more than one distinct
          value. Empty when every tournament's attributes are fully
          consistent. These are reported, never silently dropped - review
          them by hand.

    Raises:
        KeyError: If ``df`` is missing any of ``key_columns``,
            ``attribute_columns``, or ``Date``.
    """
    key_columns = list(key_columns or ["source_year", "TournamentNumber", "Location"])
    attribute_columns = list(attribute_columns or _ATTRIBUTE_COLUMNS)

    df = df.copy()

    if "source_year" in key_columns and "source_year" not in df.columns:
        df["source_year"] = pd.to_datetime(df["Date"], errors="coerce").dt.year

    required_columns = [*key_columns, *attribute_columns, "Date"]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise KeyError(f"build_tournament_table: missing required columns: {missing}")

    dates = pd.to_datetime(df["Date"], errors="coerce")

    grouped_attrs = df.groupby(key_columns)[attribute_columns]

    nunique = grouped_attrs.nunique()
    inconsistencies = nunique[(nunique > 1).any(axis=1)]

    info = grouped_attrs.agg(_mode_or_na)
    date_range = dates.groupby([df[column] for column in key_columns]).agg(
        Start_Date="min", End_Date="max"
    )

    tournaments = info.join(date_range).reset_index()

    return tournaments, inconsistencies
