"""Stage: build/update the cross-source tournament id mapping (data/mapping/).

Loads one tour+year's already-built UK and Sackmann tournament-summary tables
(`workflows.uk.tournaments.tournament_table_path` /
`workflows.sackmann.tournaments.tournament_table_path`), matches them
(`mapper.tournaments.match_uk_to_sackmann_tourneys`), and upserts two growable
reference tables under `data/mapping/tournaments/`:

- `{tour}_tournament_crosswalk.csv`: `location_key -> official_tournament_id`.
- `{tour}_tournament_source_links.csv`: long/tidy per-source id links.

Existing rows in the crosswalk always win over freshly computed ones
(`upsert_csv(..., keep="first")`) - hand corrections made directly in the CSV
are the source of truth and are never clobbered by rerunning this. Source
links use a slightly smarter merge (`_merge_source_links`): a freshly computed
row only replaces an existing one if the existing `official_tournament_id` is
still blank, so a later `manual_matches` backfill (see below) can complete a
previously-unresolved id without a hand-corrected value ever being overwritten.

If `{tour}_tournament_manual_matches.csv` exists under the same directory, it's
read and passed through to `mapper.tournaments.match_uk_to_sackmann_tourneys` -
see that function's docstring for the override format/behavior.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from ...config import settings
from ...mapper import tournaments as mapper_tournaments
from .._csv_upsert import upsert_csv
from ..sackmann.tournaments import tournament_table_path as sackmann_tournament_table_path
from ..uk.tournaments import tournament_table_path as uk_tournament_table_path

logger = logging.getLogger(__name__)


def crosswalk_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared `location_key -> official_tournament_id` crosswalk CSV."""
    tour = str(tour).lower()
    mapping_settings = settings.mapping
    mapping_dir = mapping_dir if mapping_dir is not None else settings.paths.mapping
    filename = mapping_settings.crosswalk_filename_template.format(tour=tour)
    return mapping_dir / mapping_settings.tournament_dir_name / filename


def source_links_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared per-source tournament id links CSV."""
    tour = str(tour).lower()
    mapping_settings = settings.mapping
    mapping_dir = mapping_dir if mapping_dir is not None else settings.paths.mapping
    filename = mapping_settings.source_links_filename_template.format(tour=tour)
    return mapping_dir / mapping_settings.tournament_dir_name / filename


def manual_matches_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's hand-maintained match-override CSV (read-only to this workflow)."""
    tour = str(tour).lower()
    mapping_settings = settings.mapping
    mapping_dir = mapping_dir if mapping_dir is not None else settings.paths.mapping
    filename = mapping_settings.manual_matches_filename_template.format(tour=tour)
    return mapping_dir / mapping_settings.tournament_dir_name / filename


def _load_manual_matches(path: Path) -> pd.DataFrame:
    """Read the manual-match override CSV, or an empty frame with the right columns if absent."""
    if not path.exists():
        return pd.DataFrame(columns=mapper_tournaments.MANUAL_MATCH_COLUMNS)
    df = pd.read_csv(path)
    df["official_tournament_id"] = df["official_tournament_id"].astype("Int64")
    return df


def _merge_source_links(
    existing: pd.DataFrame, new: pd.DataFrame, key_columns: list[str]
) -> pd.DataFrame:
    """Merge freshly computed source links onto the existing file.

    Like `upsert_csv(..., keep="first")`, an existing row with a filled-in
    `official_tournament_id` always wins over a freshly computed one (protects
    hand corrections). Unlike a plain `keep="first"`, a *blank* existing id is
    replaced by a freshly computed non-blank one, so a `manual_matches`
    backfill (or an improved automatic match) can complete a row that was
    previously persisted with an unresolved id.
    """
    combined = pd.concat([existing, new], ignore_index=True)
    combined["_has_id"] = combined["official_tournament_id"].notna()
    combined = combined.sort_values("_has_id", ascending=False, kind="stable")
    combined = combined.drop_duplicates(subset=key_columns, keep="first").drop(columns="_has_id")
    return combined.sort_values(key_columns).reset_index(drop=True)


def _warn_on_crosswalk_conflicts(existing: pd.DataFrame, new: pd.DataFrame) -> None:
    """Log a warning for any *bare* (non-composite) location_key whose id would
    change if `new` were upserted onto `existing`, when that location has no
    composite `location|name` keys yet.

    A single year's `build_location_crosswalk` can only detect ambiguity within
    that year's own data, so a bare location reused by a *different*
    tournament in another, separately-processed year silently keeps whichever
    id was written first (`upsert_csv(..., keep="first")`) - the conflicting
    id is dropped with no record of it ever existing. This has no way to fix
    that automatically (the composite `location|name` key needs the other
    year's tournament name, which isn't available here), but at least surfaces
    it so it can be corrected by hand (see the WTA "singapore" case, where the
    2016-2018 WTA Finals id was silently lost after a later run for 2025's
    unrelated new Singapore Open reused the same bare key).

    Once a location already has at least one composite key on file, it's a
    *known* ambiguous location - the bare key is just an arbitrary fallback
    for it, and its exact value naturally shifts across reruns without that
    being a new problem, so those are not reported here.
    """
    if existing.empty:
        return
    existing_by_key = existing.set_index("location_key")["official_tournament_id"]
    for _, row in new.iterrows():
        key = row["location_key"]
        if "|" in key or key not in existing_by_key.index:
            continue
        if any(existing_key.startswith(f"{key}|") for existing_key in existing_by_key.index):
            continue
        existing_id = existing_by_key.loc[key]
        new_id = row["official_tournament_id"]
        if pd.notna(existing_id) and pd.notna(new_id) and existing_id != new_id:
            logger.warning(
                "Crosswalk conflict for location_key=%r: existing id=%s, freshly computed id=%s "
                "- this location may need a composite location|name key to disambiguate",
                key,
                existing_id,
                new_id,
            )


class TournamentMappingResult(NamedTuple):
    """Outcome of one `build_tournament_mapping` call, for scripts/callers to report on."""

    crosswalk_path: Path
    source_links_path: Path
    uk_total: int
    sackmann_total: int
    matched_count: int
    manual_match_count: int
    review_df: pd.DataFrame
    ambiguous_locations: set[str]


def build_tournament_mapping(
    tour: str,
    year: int,
    *,
    uk_clean_dir: Path | None = None,
    sackmann_clean_dir: Path | None = None,
    mapping_dir: Path | None = None,
    min_match_score: float | None = None,
) -> TournamentMappingResult:
    """Match one tour+year's UK/Sackmann tournaments and upsert the mapping tables.

    Requires both tours' tournament-summary tables to already exist for `year`
    (see `workflows.uk.build_uk_tournaments`/`workflows.sackmann.build_sackmann_tournaments`).

    Raises:
        FileNotFoundError: if either tournament-summary table doesn't exist yet.

    """
    tour = str(tour).lower()
    min_match_score = (
        min_match_score if min_match_score is not None else settings.mapping.min_match_score
    )

    uk_path = uk_tournament_table_path(tour, uk_clean_dir)
    if not uk_path.exists():
        raise FileNotFoundError(f"No UK tournament table at {uk_path} - build it first")
    sackmann_path = sackmann_tournament_table_path(tour, sackmann_clean_dir)
    if not sackmann_path.exists():
        raise FileNotFoundError(f"No Sackmann tournament table at {sackmann_path} - build it first")

    df_uk = pd.read_csv(uk_path)
    df_uk = df_uk.loc[df_uk["year"] == year].reset_index(drop=True)

    df_sackmann = pd.read_csv(sackmann_path)
    df_sackmann = df_sackmann.loc[
        (df_sackmann["year"] == year) & (df_sackmann["tourney_level"] != "D")
    ].reset_index(drop=True)

    manual_matches = _load_manual_matches(manual_matches_path(tour, mapping_dir))

    match_result = mapper_tournaments.match_uk_to_sackmann_tourneys(
        df_uk, df_sackmann, year, min_match_score=min_match_score, manual_matches=manual_matches
    )
    crosswalk_result = mapper_tournaments.build_location_crosswalk(match_result.link_df, df_uk)
    source_links = mapper_tournaments.build_source_links(match_result.link_df)

    crosswalk_csv_path = crosswalk_path(tour, mapping_dir)
    if crosswalk_csv_path.exists():
        _warn_on_crosswalk_conflicts(pd.read_csv(crosswalk_csv_path), crosswalk_result.crosswalk)
    upsert_csv(
        crosswalk_csv_path, crosswalk_result.crosswalk, key_columns=["location_key"], keep="first"
    )

    source_links_csv_path = source_links_path(tour, mapping_dir)
    source_links_csv_path.parent.mkdir(parents=True, exist_ok=True)
    key_columns = ["source", "year", "source_tournament_id"]
    if source_links_csv_path.exists():
        existing_source_links = pd.read_csv(source_links_csv_path)
        source_links = _merge_source_links(existing_source_links, source_links, key_columns)
    else:
        source_links = source_links.sort_values(key_columns).reset_index(drop=True)
    source_links.to_csv(source_links_csv_path, index=False)

    logger.info(
        "[%s %s] Matched %d/%d UK and %d/%d Sackmann tournaments -> %s, %s",
        tour.upper(),
        year,
        match_result.matched_count,
        match_result.uk_total,
        match_result.matched_count,
        match_result.sackmann_total,
        crosswalk_csv_path,
        source_links_csv_path,
    )
    if crosswalk_result.ambiguous_locations:
        logger.info(
            "[%s %s] Ambiguous locations (resolved via location+name): %s",
            tour.upper(),
            year,
            sorted(crosswalk_result.ambiguous_locations),
        )

    return TournamentMappingResult(
        crosswalk_path=crosswalk_csv_path,
        source_links_path=source_links_csv_path,
        uk_total=match_result.uk_total,
        sackmann_total=match_result.sackmann_total,
        matched_count=match_result.matched_count,
        manual_match_count=match_result.manual_match_count,
        review_df=match_result.review_df,
        ambiguous_locations=crosswalk_result.ambiguous_locations,
    )


__all__ = [
    "TournamentMappingResult",
    "build_tournament_mapping",
    "crosswalk_path",
    "manual_matches_path",
    "source_links_path",
]
