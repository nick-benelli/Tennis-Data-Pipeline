"""Tournament-level summaries derived from Tennis-Data UK match data."""

from __future__ import annotations

from typing import NamedTuple

import pandas as pd

# Attributes expected to be constant for every match within a tournament (raw schema).
_ATTRIBUTE_COLUMNS = ["Tournament", "Series", "Court", "Surface", "Best of"]

# Key/attribute defaults for the cleaned schema (clean_uk_atp_data/clean_uk_wta_data
# output, e.g. loader.uk.load_clean_uk_year/load_clean_uk_combined). "tour" is
# included so combining ATP+WTA data doesn't collide same-numbered tournament ids.
CLEAN_TOURNAMENT_KEY_COLUMNS = ["tour", "year", "uk_tournament_id", "location"]
CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS = [
    "tournament_name",
    "series",
    "surface",
    "best_of",
    "is_outdoor",
]


def _mode_or_na(series: pd.Series) -> object:
    """Most frequent value in the group (smooths over stray data-entry errors)."""
    mode = series.mode()
    return mode.iloc[0] if not mode.empty else pd.NA


def _champion_match_stats(
    df: pd.DataFrame,
    key_columns: list[str],
    winner_column: str,
    champion: pd.Series,
    rank_column: str | None,
    odds_column: str | None,
) -> pd.DataFrame:
    """Mean of `rank_column`/`odds_column` across the champion's own matches (they won every one)."""
    keyed = df.set_index(key_columns)
    is_champion_match = (keyed[winner_column] == champion.reindex(keyed.index)).fillna(False)
    champion_matches = keyed[is_champion_match]
    grouped_champion = champion_matches.groupby(level=key_columns)

    stats = {}
    if rank_column and rank_column in df.columns:
        stats["champion_avg_rank"] = grouped_champion[rank_column].mean().round(4)
    if odds_column and odds_column in df.columns:
        stats["champion_avg_odds"] = grouped_champion[odds_column].mean().round(4)

    return pd.DataFrame(stats)


class TournamentTable(NamedTuple):
    """Result of `build_tournament_table`/`build_uk_tournament_table`.

    Still unpacks as a 2-tuple (``tournaments, inconsistencies = ...``), but
    also supports named access (``result.tournaments``) so call sites that
    hold onto the result don't have to remember the positional order.
    """

    tournaments: pd.DataFrame
    inconsistencies: pd.DataFrame


def build_tournament_table(
    df: pd.DataFrame,
    *,
    key_columns: list[str] | None = None,
    attribute_columns: list[str] | None = None,
    date_column: str = "Date",
    start_date_column: str = "Start_Date",
    end_date_column: str = "End_Date",
    winner_column: str | None = None,
    loser_column: str | None = None,
    round_column: str | None = None,
    final_round_value: str = "F",
    match_status_column: str | None = None,
    rank_column: str | None = None,
    odds_column: str | None = None,
) -> TournamentTable:
    """Derive one row per tournament from match-level Tennis-Data UK data.

    Tournament number columns (``ATP``/``WTA``, or ``TournamentNumber`` after
    ``clean_matches``) are reused across seasons and, on rare weeks, across
    concurrent tournaments in the same season. ``key_columns`` must include
    enough columns to disambiguate those cases: ``source_year`` when combining
    multiple seasons, and ``Location`` to split same-week collisions within a
    season.

    Args:
        df: Match-level data containing ``date_column``, ``key_columns``, and
            ``attribute_columns`` (e.g. the output of ``atp.load_year``/
            ``wta.load_year``, or a Tennis-Data UK season CSV read as-is).
        key_columns: Columns that together uniquely identify a tournament.
            Defaults to ``["source_year", "TournamentNumber", "Location"]``.
            If ``source_year`` is requested but absent, it is derived from
            ``date_column``.
        attribute_columns: Columns expected to be constant within a
            tournament. Defaults to
            ``["Tournament", "Series", "Court", "Surface", "Best of"]``.
        date_column: Column holding each match's date. Defaults to ``"Date"``
            (the raw Tennis-Data UK column name); pass ``"match_date"`` for
            data produced by ``clean_uk_atp_data``/``clean_uk_wta_data``.
        start_date_column: Output column name for the tournament's earliest
            match date. Defaults to ``"Start_Date"``.
        end_date_column: Output column name for the tournament's latest match
            date. Defaults to ``"End_Date"``.
        winner_column: Column holding each match's winner name. When given
            (together with ``loser_column``), adds a ``num_players`` column
            (distinct entrants). Optional - omit to skip it.
        loser_column: Column holding each match's loser name. See
            ``winner_column``.
        round_column: Column holding each match's round code. When given,
            adds a ``num_rounds`` column (distinct rounds played); when given
            together with ``winner_column``/``loser_column``, also adds
            ``champion``/``runner_up`` from the tournament's final (the row
            where ``round_column == final_round_value``). Optional - omit to
            skip these.
        final_round_value: Value of ``round_column`` identifying the final.
            Defaults to ``"F"`` (the canonical round code used by
            ``clean_uk_atp_data``/``clean_uk_wta_data``).
        match_status_column: Column holding each match's status (e.g.
            "completed"/"retired"/"walkover"). When given, adds one
            ``num_<status>_matches`` column per distinct status seen anywhere
            in ``df`` (0 for tournaments without that status). Optional -
            omit to skip it.
        rank_column: Column holding each match's winner rank (e.g.
            ``"winner_rank"``). When given together with ``round_column``/
            ``winner_column``/``loser_column``, adds ``champion_avg_rank``
            (mean across the champion's matches in the tournament). Optional.
        odds_column: Column holding each match's winner odds (e.g.
            ``"odds_avg_winner"``). Same requirements/behavior as
            ``rank_column``, adding ``champion_avg_odds``. Optional.

    Returns:
        A `TournamentTable` (``tournaments``, ``inconsistencies``):

        - ``tournaments``: one row per tournament with the most common value
          of each attribute column; ``start_date_column``/``end_date_column``;
          ``num_matches``; and, if requested, ``num_rounds``/``num_players``/
          ``champion``/``runner_up``/``num_<status>_matches``/
          ``champion_avg_rank``/``champion_avg_odds``. ``champion``/
          ``runner_up``/``champion_avg_rank``/``champion_avg_odds`` are ``NA``
          for tournaments whose final wasn't played/recorded.
        - ``inconsistencies``: per-key counts of distinct values for each
          attribute column, filtered to keys with more than one distinct
          value. Empty when every tournament's attributes are fully
          consistent. These are reported, never silently dropped - review
          them by hand.

    Raises:
        KeyError: If ``df`` is missing any of ``key_columns``,
            ``attribute_columns``, or ``date_column``.

    """
    key_columns = list(key_columns or ["source_year", "TournamentNumber", "Location"])
    attribute_columns = list(attribute_columns or _ATTRIBUTE_COLUMNS)

    df = df.copy()

    if "source_year" in key_columns and "source_year" not in df.columns:
        df["source_year"] = pd.to_datetime(df[date_column], format="mixed", errors="coerce").dt.year

    required_columns = [*key_columns, *attribute_columns, date_column]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise KeyError(f"build_tournament_table: missing required columns: {missing}")

    # Date format drifts across seasons (e.g. "1/1/23" vs. "2023-01-01"), so
    # infer per-element rather than assuming one format for every row.
    df["_parsed_date"] = pd.to_datetime(df[date_column], format="mixed", errors="coerce")

    grouped = df.groupby(key_columns)
    grouped_attrs = grouped[attribute_columns]

    nunique = grouped_attrs.nunique()
    inconsistencies = nunique[(nunique > 1).any(axis=1)]

    info = grouped_attrs.agg(_mode_or_na)
    date_range = grouped["_parsed_date"].agg(["min", "max"])
    date_range.columns = [start_date_column, end_date_column]
    num_matches = grouped.size().rename("num_matches")

    tournaments = info.join([date_range, num_matches])

    has_round = round_column and round_column in df.columns
    has_winner_loser = (
        winner_column and loser_column and winner_column in df.columns and loser_column in df.columns
    )

    if has_round:
        # has_round already confirmed round_column is a real column, so it can't be None.
        assert round_column is not None
        tournaments = tournaments.join(grouped[round_column].nunique().rename("num_rounds"))

    if match_status_column and match_status_column in df.columns:
        status_counts = grouped[match_status_column].value_counts().unstack(fill_value=0)
        status_counts.columns = [f"num_{status}_matches" for status in status_counts.columns]
        tournaments = tournaments.join(status_counts)

    if has_winner_loser:
        # has_winner_loser already confirmed both are non-None; re-assert so
        # mypy narrows them from `str | None` for the calls below.
        assert winner_column is not None
        assert loser_column is not None

        participants = pd.concat(
            [
                df[[*key_columns, winner_column]].rename(columns={winner_column: "_player"}),
                df[[*key_columns, loser_column]].rename(columns={loser_column: "_player"}),
            ]
        )
        num_players = participants.groupby(key_columns)["_player"].nunique().rename("num_players")
        tournaments = tournaments.join(num_players)

        if has_round:
            finals = df[df[round_column] == final_round_value]
            champion = finals.groupby(key_columns)[winner_column].first().rename("champion")
            runner_up = finals.groupby(key_columns)[loser_column].first().rename("runner_up")
            tournaments = tournaments.join([champion, runner_up])

            if rank_column or odds_column:
                champion_stats = _champion_match_stats(
                    df, key_columns, winner_column, champion, rank_column, odds_column
                )
                tournaments = tournaments.join(champion_stats)

    tournaments = tournaments.reset_index()

    return TournamentTable(tournaments, inconsistencies)


def build_uk_tournament_table(
    df: pd.DataFrame,
    *,
    key_columns: list[str] | None = None,
    attribute_columns: list[str] | None = None,
) -> TournamentTable:
    """`build_tournament_table` for cleaned Tennis-Data UK data.

    Convenience wrapper defaulting to the canonical clean-schema column names
    (``tour``/``year``/``uk_tournament_id``/``location`` as the key,
    ``tournament_name``/``series``/``surface``/``best_of``/``is_outdoor`` as
    the attributes, ``match_date`` as the date column) produced by
    ``clean_uk_atp_data``/``clean_uk_wta_data`` - e.g. the output of
    ``loader.uk.load_clean_uk_year``/``load_clean_uk_combined``. Also adds
    ``start_date``/``end_date``, ``num_matches``, ``num_rounds``,
    ``num_players``, ``champion``, ``runner_up``, one ``num_<status>_matches``
    column per match status seen (e.g. ``num_completed_matches``,
    ``num_retired_matches``, ``num_walkover_matches``), and the champion's
    ``champion_avg_rank``/``champion_avg_odds`` across their matches in the
    tournament. ``champion``/``runner_up``/the champion averages are ``NA``
    for tournaments whose final wasn't played/recorded.
    """
    return build_tournament_table(
        df,
        key_columns=key_columns or CLEAN_TOURNAMENT_KEY_COLUMNS,
        attribute_columns=attribute_columns or CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS,
        date_column="match_date",
        start_date_column="start_date",
        end_date_column="end_date",
        winner_column="winner_name",
        loser_column="loser_name",
        round_column="round",
        match_status_column="match_status",
        rank_column="winner_rank",
        odds_column="odds_avg_winner",
    )


__all__ = [
    "CLEAN_TOURNAMENT_ATTRIBUTE_COLUMNS",
    "CLEAN_TOURNAMENT_KEY_COLUMNS",
    "TournamentTable",
    "build_tournament_table",
    "build_uk_tournament_table",
]
