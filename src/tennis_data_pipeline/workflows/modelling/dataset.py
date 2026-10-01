"""Build the curated Sackmann+UK merged dataset used for downstream EDA/modelling.

Column-selection rules mirror notebooks/dev/explore-linked-data.ipynb's
"Feature audit" cells: prefer Sackmann's version of any column duplicated
between the two sources (confirmed near-100% agreement there - see the
notebook), keep UK's betting odds/series/location (Sackmann has no
equivalent), and keep the linkage QA columns (`match_method`/`review_flag`/
`data_quality_flag`) so downstream consumers can filter low-confidence rows
themselves rather than have that decision baked in here.

`minutes`, the `w_*`/`l_*` serve stats, and the per-set score/tiebreak
columns are only known *after* a match is played - fine for descriptive EDA,
but a leakage risk if used as predictors for a pre-match outcome model.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from ...config import settings
from ...datasources.sackmann.client import Tour
from ...loader.linked import enriched_matches as linked_loader
from ..sackmann import matches as sackmann_matches

# Columns present (under the same name) in both the Sackmann and UK-enriched
# frames before the merge - suffixed "_sack"/"_uk" by `pd.merge(...,
# suffixes=(...))`. Sackmann is the gold-standard source, so every one of
# these keeps its "_sack" value under the unsuffixed name; the "_uk"
# duplicate is dropped.
_SHARED_CONCEPTS = [
    "best_of",
    "canonical_match_key",
    "loser_name",
    "loser_rank",
    "loser_rank_points",
    "match_status",
    "round",
    "surface",
    "tour",
    "winner_name",
    "winner_rank",
    "winner_rank_points",
]

CORE_SACKMANN_COLUMNS = (
    [
        "canonical_match_key",
        "tourney_id",
        "tourney_name",
        "tourney_date",
        "tourney_level",
        "draw_size",
        "match_num",
        "surface",
        "round",
        "best_of",
        "match_status",
        "winner_id",
        "winner_name",
        "winner_hand",
        "winner_ht",
        "winner_ioc",
        "winner_age",
        "winner_seed",
        "winner_entry",
        "loser_id",
        "loser_name",
        "loser_hand",
        "loser_ht",
        "loser_ioc",
        "loser_age",
        "loser_seed",
        "loser_entry",
        "winner_rank",
        "winner_rank_points",
        "loser_rank",
        "loser_rank_points",
        "score",
        "minutes",
        "sets_played",
        "w_ace",
        "w_df",
        "w_svpt",
        "w_1stIn",
        "w_1stWon",
        "w_2ndWon",
        "w_SvGms",
        "w_bpSaved",
        "w_bpFaced",
        "l_ace",
        "l_df",
        "l_svpt",
        "l_1stIn",
        "l_1stWon",
        "l_2ndWon",
        "l_SvGms",
        "l_bpSaved",
        "l_bpFaced",
    ]
    + [f"set{i}_{side}" for i in range(1, 6) for side in ("winner", "loser")]
    + [f"set{i}_tiebreak_{side}" for i in range(1, 6) for side in ("winner", "loser")]
)

# Things Sackmann has no equivalent for at all.
UK_SUPPLEMENTAL_COLUMNS = [
    "odds_b365_winner",
    "odds_b365_loser",
    "odds_pinnacle_winner",
    "odds_pinnacle_loser",
    "odds_max_winner",
    "odds_max_loser",
    "odds_avg_winner",
    "odds_avg_loser",
    "series",
    "location",
    "is_outdoor",
    "players_remaining",
]

# Linkage QA - kept for filtering, not as modelling features.
LINKAGE_QA_COLUMNS = ["match_method", "review_flag", "data_quality_flag"]

# "tour" is constant within a single `build_match_dataset` call, but real
# signal once `build_match_dataset_for_years`/multiple tours are concatenated.
MODEL_COLUMNS = ["tour"] + CORE_SACKMANN_COLUMNS + UK_SUPPLEMENTAL_COLUMNS + LINKAGE_QA_COLUMNS


def build_match_dataset(tour: Tour | str, year: int, *, chronological: bool = False) -> pd.DataFrame:
    """Merge one tour+year's Sackmann and UK-enriched matches into the curated model columns.

    Pass `chronological=True` to load the Sackmann side in chronological
    order (see `workflows.sackmann.matches.load_local_matches`) - the inner
    join preserves that row order (one UK match per `canonical_match_key`).
    """
    tour = Tour(str(tour).lower())
    df_sack = sackmann_matches.load_local_matches(tour, [year], chronological=chronological)
    df_uk = linked_loader.load_enriched_matches(tour.value, year)

    df_merge = pd.merge(df_sack, df_uk, how="inner", on="canonical_match_key", suffixes=("_sack", "_uk"))
    df_merge = df_merge.rename(columns={f"{concept}_sack": concept for concept in _SHARED_CONCEPTS})
    df_merge["tour"] = tour.value

    return df_merge[MODEL_COLUMNS]


def build_match_dataset_for_years(
    tour: Tour | str, years: Iterable[int], *, chronological: bool = False
) -> pd.DataFrame:
    """Concatenate `build_match_dataset` across several years for one tour."""
    frames = [build_match_dataset(tour, year, chronological=chronological) for year in years]
    return pd.concat(frames, ignore_index=True)


def discover_available_years(tour: Tour | str, linked_dir: Path | None = None) -> list[int]:
    """List the years with a persisted `data/linked/{tour}/{year}/` enrichment output.

    This (not the local Sackmann archive, which covers a much wider range) is
    the limiting factor for which years can be merged.
    """
    tour = Tour(str(tour).lower())
    base = (linked_dir if linked_dir is not None else settings.paths.linked) / tour.value
    if not base.is_dir():
        return []
    return sorted(int(entry.name) for entry in base.iterdir() if entry.is_dir() and entry.name.isdigit())


__all__ = [
    "CORE_SACKMANN_COLUMNS",
    "LINKAGE_QA_COLUMNS",
    "MODEL_COLUMNS",
    "UK_SUPPLEMENTAL_COLUMNS",
    "build_match_dataset",
    "build_match_dataset_for_years",
    "discover_available_years",
]
