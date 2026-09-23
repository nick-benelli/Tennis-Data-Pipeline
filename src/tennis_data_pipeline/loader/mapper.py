"""Load cross-source tournament id mapping CSVs (data/mapping/tournaments/) with dtypes restored.

`official_tournament_id` is a nullable int in memory (`mapper.tournaments` always
produces it as `Int64`), but a plain `pd.read_csv` round-trip loses that - any
missing id makes pandas infer the whole column as `float64` (e.g. `301` reads
back as `301.0`). This restores it to `Int64` for anything read from
`data/mapping/tournaments/`, the same pattern `loader.uk` uses for the clean
match CSVs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# from tennis_data_pipeline.config import settings
# from tennis_data_pipeline.mapper.tournaments import MANUAL_MATCH_COLUMNS
from ..config import settings
from ..mapper.tournaments import MANUAL_MATCH_COLUMNS

CROSSWALK_COLUMNS = ["location_key", "official_tournament_id", "location"]
SOURCE_LINKS_COLUMNS = ["official_tournament_id", "year", "source", "source_tournament_id"]


def _tournament_mapping_path(tour: str, mapping_dir: Path | None, filename_template: str) -> Path:
    tour = str(tour).lower()
    mapping_settings = settings.mapping
    mapping_dir = mapping_dir if mapping_dir is not None else settings.paths.mapping
    filename = filename_template.format(tour=tour)
    return mapping_dir / mapping_settings.tournament_dir_name / filename


def crosswalk_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared `location_key -> official_tournament_id` crosswalk CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.crosswalk_filename_template)


def source_links_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's shared per-source tournament id links CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.source_links_filename_template)


def manual_matches_path(tour: str, mapping_dir: Path | None = None) -> Path:
    """Path for one tour's hand-maintained match-override CSV."""
    return _tournament_mapping_path(tour, mapping_dir, settings.mapping.manual_matches_filename_template)


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


__all__ = [
    "CROSSWALK_COLUMNS",
    "SOURCE_LINKS_COLUMNS",
    "crosswalk_path",
    "load_tournament_crosswalk",
    "load_tournament_manual_matches",
    "load_tournament_source_links",
    "manual_matches_path",
    "source_links_path",
]
