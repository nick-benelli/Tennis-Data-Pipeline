"""Load cross-source mapping CSVs (data/mapping/) with dtypes restored.

`official_tournament_id` is a nullable int in memory (`mapper.tournaments` always
produces it as `Int64`), but a plain `pd.read_csv` round-trip loses that - any
missing id makes pandas infer the whole column as `float64` (e.g. `301` reads
back as `301.0`). This restores it to `Int64` for anything read from
`data/mapping/`, the same pattern `loader.uk` uses for the clean match CSVs.

Covers both `mapper.tournaments` (tournament id crosswalk, under
`data/mapping/tournaments/`) and `mapper.matches` (Pass-1 match-link crosswalk,
under `data/mapping/matches/`).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..config import settings
from ..mapper.matches import MANUAL_LINKS_COLUMNS
from ..mapper.tournaments import MANUAL_MATCH_COLUMNS

CROSSWALK_COLUMNS = ["location_key", "official_tournament_id", "location"]
SOURCE_LINKS_COLUMNS = ["official_tournament_id", "year", "source", "source_tournament_id"]


def _mapping_path(tour: str, mapping_dir: Path | None, dir_name: str, filename_template: str) -> Path:
    tour = str(tour).lower()
    mapping_dir = mapping_dir if mapping_dir is not None else settings.paths.mapping
    filename = filename_template.format(tour=tour)
    return mapping_dir / dir_name / filename


def _tournament_mapping_path(tour: str, mapping_dir: Path | None, filename_template: str) -> Path:
    return _mapping_path(tour, mapping_dir, settings.mapping.tournament_dir_name, filename_template)


def _match_mapping_path(tour: str, mapping_dir: Path | None, filename_template: str) -> Path:
    return _mapping_path(tour, mapping_dir, settings.mapping.match_dir_name, filename_template)


def crosswalk_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared `location_key -> official_tournament_id` crosswalk CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.crosswalk_filename_template)


def source_links_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared per-source tournament id links CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.source_links_filename_template)


def manual_matches_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's hand-maintained match-override CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.manual_matches_filename_template)


def manual_match_links_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's hand-maintained, match-level manual-link override CSV (Pass 0)."""
    return _match_mapping_path(tour, mapping_dir, settings.mapping.match_manual_links_filename_template)


def _read_with_official_id_as_int64(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path)
    df["official_tournament_id"] = pd.to_numeric(df["official_tournament_id"], errors="coerce").astype(
        "Int64"
    )
    return df


def load_tournament_crosswalk(tour: str, mapping_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour's `location_key -> official_tournament_id` crosswalk with dtypes restored.

    Returns an empty frame with the right columns if the file doesn't exist yet.
    """
    return _read_with_official_id_as_int64(crosswalk_path(tour, mapping_dir), CROSSWALK_COLUMNS)


def load_tournament_source_links(tour: str, mapping_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour's long/tidy per-source tournament id links CSV with dtypes restored.

    Returns an empty frame with the right columns if the file doesn't exist yet.
    """
    return _read_with_official_id_as_int64(source_links_path(tour, mapping_dir), SOURCE_LINKS_COLUMNS)


def load_tournament_manual_matches(tour: str, mapping_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour's hand-maintained match-override CSV with dtypes restored.

    Returns an empty frame with the right columns if the file doesn't exist yet.
    """
    return _read_with_official_id_as_int64(manual_matches_path(tour, mapping_dir), MANUAL_MATCH_COLUMNS)


def load_manual_match_links(tour: str, mapping_dir: Path | None = None) -> pd.DataFrame:
    """Load one tour's hand-maintained, match-level manual-link override CSV (Pass 0).

    Returns an empty frame with the right columns if the file doesn't exist yet.
    """
    path = manual_match_links_path(tour, mapping_dir)
    if not path.exists():
        return pd.DataFrame(columns=MANUAL_LINKS_COLUMNS)
    return pd.read_csv(path)


__all__ = [
    "CROSSWALK_COLUMNS",
    "SOURCE_LINKS_COLUMNS",
    "crosswalk_path",
    "load_manual_match_links",
    "load_tournament_crosswalk",
    "load_tournament_manual_matches",
    "load_tournament_source_links",
    "manual_match_links_path",
    "manual_matches_path",
    "source_links_path",
]
