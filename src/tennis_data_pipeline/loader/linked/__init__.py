"""Load the formalized per-year UK<->Sackmann linkage outputs (data/linked/{tour}/{year}/).

See `mapper.matches.uk_sackmann.outputs` for how these tables are built, and
`workflows.mapper.matches.uk_sackmann` for the layer that writes them.

Split across `paths` (path resolution), `match_links`, and `enriched_matches`
(one dtype-restoring loader each) - re-exported here so callers keep using
`loader.linked.load_match_links`, etc. unchanged.
"""

from __future__ import annotations

from .enriched_matches import load_enriched_matches
from .match_links import load_match_links
from .paths import (
    all_years_summary_path,
    enriched_matches_path,
    linkage_ambiguous_path,
    linkage_summary_path,
    linkage_unmatched_path,
    match_crosswalk_path,
    year_output_dir,
)

__all__ = [
    "all_years_summary_path",
    "enriched_matches_path",
    "linkage_ambiguous_path",
    "linkage_summary_path",
    "linkage_unmatched_path",
    "load_enriched_matches",
    "load_match_links",
    "match_crosswalk_path",
    "year_output_dir",
]
