"""Stage: run Pass 0 + Pass 1 + Pass 2 match linking and persist the formalized per-year outputs.

Loads one tour+year's clean UK matches (`loader.uk.load_clean_uk_year`),
Sackmann matches (`datasources.sackmann.atp/wta.load_year`), the tournament
source-links crosswalk (`loader.mapper.load_tournament_source_links`), and the
hand-maintained manual-link override table (`loader.mapper.load_manual_match_links`),
links them (`mapper.matches.build_manual_rank_and_name_links`: Pass 0 manual
overrides resolved first, then Pass 1 rank + Pass 2 name-pair on what's left),
reshapes the result into the formalized output tables
(`mapper.matches.build_match_crosswalk` / `build_enriched_matches` /
`finalize_link_status` / `build_linkage_summary`), and persists five tables
under `data/linked/{tour}/{year}/`:

- `{tour}_match_links_{year}.csv`: the compact lineage crosswalk.
- `{tour}_matches_enriched_{year}.csv`: every UK match row + linkage/canonical
  columns, for downstream analysis.
- `{tour}_linkage_summary_{year}.csv`: one coverage/health row.
- `review/{tour}_linkage_ambiguous_{year}.csv` /
  `review/{tour}_linkage_unmatched_{year}.csv`: the pipeline's *final*
  ambiguous/unmatched residuals (after both passes), for debugging.

Each year's outputs are overwritten independently on rerun - other years'
files are never touched, and the raw/clean inputs are never modified. This
run also rebuilds the all-years rollup at
`data/linked/{tour}/{tour}_linkage_summary.csv` (one row per year) by
re-concatenating every year's persisted `{tour}_linkage_summary_{year}.csv` -
those per-year files are the source of truth, so the rollup is always fully
reconstructible and safe to delete at any time (see `rebuild_all_years_summary`).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from ....config import settings
from ....datasources import sackmann as sk
from ....loader.linked import (
    all_years_summary_path,
    enriched_matches_path,
    linkage_ambiguous_path,
    linkage_summary_path,
    linkage_unmatched_path,
    match_crosswalk_path,
    year_output_dir,
)
from ....loader.mapper import (
    load_manual_match_links,
    load_tournament_source_links,
    manual_match_links_path,
)
from ....loader.uk import load_clean_uk_year
from ....mapper.matches import (
    LINKAGE_SUMMARY_COLUMNS,
    add_unmatched_diagnostics,
    build_enriched_matches,
    build_linkage_summary,
    build_manual_rank_and_name_links,
    build_match_crosswalk,
    finalize_link_status,
)

logger = logging.getLogger(__name__)


def write_linkage_outputs(
    *,
    output_dir: Path,
    year: int,
    tour: str,
    match_links: pd.DataFrame,
    enriched_matches: pd.DataFrame,
    ambiguous: pd.DataFrame,
    unmatched: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    """Write the five formalized output tables under `output_dir` (creating dirs as needed)."""
    review_dir = output_dir / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    match_links.to_csv(match_crosswalk_path(output_dir, tour, year), index=False)
    enriched_matches.to_csv(enriched_matches_path(output_dir, tour, year), index=False)
    summary.to_csv(linkage_summary_path(output_dir, tour, year), index=False)
    ambiguous.to_csv(linkage_ambiguous_path(output_dir, tour, year), index=False)
    unmatched.to_csv(linkage_unmatched_path(output_dir, tour, year), index=False)


class MatchLinkingResult(NamedTuple):
    """Outcome of one `build_match_links` call, for scripts/callers to report on."""

    output_dir: Path
    uk_total: int
    linked_count: int
    linked_manual: int
    linked_pass_1: int
    linked_pass_2: int
    ambiguous_count: int
    unmatched_count: int


def rebuild_all_years_summary(tour: str, linked_dir: Path | None = None) -> pd.DataFrame:
    """Rebuild the all-years rollup entirely from each year's persisted summary file.

    The per-year `{tour}_linkage_summary_{year}.csv` files are the source of
    truth - this rollup is a fully-derived convenience view over them, never
    independent state, so it's safe to delete at any time: the next
    `build_match_links` call (or a direct call here) reconstructs it from
    scratch by scanning every year folder that's already been linked, rather
    than trying to incrementally patch a persisted copy that could drift.
    """
    tour = str(tour).lower()
    base = linked_dir if linked_dir is not None else settings.paths.linked
    tour_dir = base / tour

    rows: list[pd.DataFrame] = []
    if tour_dir.exists():
        for year_dir in sorted(tour_dir.iterdir()):
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue
            summary_path = linkage_summary_path(year_dir, tour, int(year_dir.name))
            if summary_path.exists():
                rows.append(pd.read_csv(summary_path))

    combined = (
        pd.concat(rows, ignore_index=True).sort_values("year").reset_index(drop=True)
        if rows
        else pd.DataFrame(columns=LINKAGE_SUMMARY_COLUMNS)
    )

    path = all_years_summary_path(tour, linked_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(path, index=False)
    return combined


def build_match_links(
    tour: str,
    year: int,
    *,
    mapping_dir: Path | None = None,
    linked_dir: Path | None = None,
) -> MatchLinkingResult:
    """Run Pass 0 + Pass 1 + Pass 2 match linking for one tour+year and persist the formalized outputs.

    Raises:
        FileNotFoundError: if that year's clean UK match CSV doesn't exist yet
            (see `workflows.uk.build_uk_atp_data`/`build_uk_wta_data`).

    """
    tour = str(tour).lower()
    sk_tour = sk.atp if tour == "atp" else sk.wta

    uk_df = load_clean_uk_year(tour, year)
    sackmann_df = sk_tour.load_year(year)
    tournament_mapper_df = load_tournament_source_links(tour, mapping_dir)
    manual_links_df = load_manual_match_links(tour, mapping_dir)

    accepted, ambiguous_raw, unmatched_raw = build_manual_rank_and_name_links(
        uk_df, sackmann_df, tournament_mapper_df, manual_links_df
    )
    ambiguous, unmatched = finalize_link_status(accepted, ambiguous_raw, unmatched_raw)
    unmatched = add_unmatched_diagnostics(unmatched)

    match_links = build_match_crosswalk(accepted)
    enriched_matches = build_enriched_matches(uk_df, sackmann_df, accepted)
    summary = build_linkage_summary(
        uk_df, sackmann_df, accepted, ambiguous, unmatched, year=year, tour=tour
    )
    summary["linked_at"] = datetime.now(UTC).isoformat()

    output_dir = year_output_dir(tour, year, linked_dir)
    write_linkage_outputs(
        output_dir=output_dir,
        year=year,
        tour=tour,
        match_links=match_links,
        enriched_matches=enriched_matches,
        ambiguous=ambiguous,
        unmatched=unmatched,
        summary=summary,
    )
    rebuild_all_years_summary(tour, linked_dir)

    summary_row = summary.iloc[0]
    logger.info(
        "[%s %s] uk_matches=%d linked=%d (manual=%d pass1=%d pass2=%d) ambiguous=%d unmatched=%d -> %s",
        tour.upper(),
        year,
        summary_row["uk_total_matches"],
        summary_row["linked_matches"],
        summary_row["linked_manual"],
        summary_row["linked_pass_1"],
        summary_row["linked_pass_2"],
        summary_row["ambiguous_matches"],
        summary_row["unmatched_matches"],
        output_dir,
    )

    return MatchLinkingResult(
        output_dir=output_dir,
        uk_total=int(summary_row["uk_total_matches"]),
        linked_count=int(summary_row["linked_matches"]),
        linked_manual=int(summary_row["linked_manual"]),
        linked_pass_1=int(summary_row["linked_pass_1"]),
        linked_pass_2=int(summary_row["linked_pass_2"]),
        ambiguous_count=int(summary_row["ambiguous_matches"]),
        unmatched_count=int(summary_row["unmatched_matches"]),
    )


__all__ = [
    "MatchLinkingResult",
    "all_years_summary_path",
    "build_match_links",
    "enriched_matches_path",
    "linkage_ambiguous_path",
    "linkage_summary_path",
    "linkage_unmatched_path",
    "manual_match_links_path",
    "match_crosswalk_path",
    "rebuild_all_years_summary",
    "write_linkage_outputs",
    "year_output_dir",
]
