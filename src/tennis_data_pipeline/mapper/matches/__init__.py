"""Cross-source match-level linking (data/mapping/matches/).

Currently just Tennis-Data UK <-> Sackmann (`.uk_sackmann`); a different
source pair would get its own sibling submodule here later, following the
same schema/tournament_ids/names/pass1/pass2/pipeline split.

    from tennis_data_pipeline.mapper.matches import build_rank_links, build_rank_and_name_links
"""

from __future__ import annotations

from .uk_sackmann import (
    CROSSWALK_COLUMNS,
    ENRICHED_LINKAGE_BLOCK_COLUMNS,
    LINKAGE_SUMMARY_COLUMNS,
    MANUAL_LINKS_COLUMNS,
    MATCH_CROSSWALK_COLUMNS,
    MATCH_METHOD_MANUAL,
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
    NAME_PAIR_CROSSWALK_COLUMNS,
    NAME_PAIR_KEY_COLUMNS,
    RANK_CANDIDATE_KEY_COLUMNS,
    SourcePlayerName,
    add_sackmann_match_key,
    add_unmatched_diagnostics,
    attach_tournament_ids,
    build_enriched_matches,
    build_linkage_summary,
    build_manual_links,
    build_manual_rank_and_name_links,
    build_match_crosswalk,
    build_name_pair_links,
    build_rank_and_name_links,
    build_rank_links,
    classify_name_pair_candidates,
    classify_rank_candidates,
    finalize_link_status,
    generate_name_pair_candidates,
    generate_rank_candidates,
    linkage_summary,
    normalize_name,
    parse_tennis_data_name,
    player_name_compatible,
    tournament_linkage_summary,
)

__all__ = [
    "CROSSWALK_COLUMNS",
    "ENRICHED_LINKAGE_BLOCK_COLUMNS",
    "LINKAGE_SUMMARY_COLUMNS",
    "MANUAL_LINKS_COLUMNS",
    "MATCH_CROSSWALK_COLUMNS",
    "MATCH_METHOD_MANUAL",
    "MATCH_METHOD_TOURNAMENT_RANK_UNIQUE",
    "MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR",
    "NAME_PAIR_CROSSWALK_COLUMNS",
    "NAME_PAIR_KEY_COLUMNS",
    "RANK_CANDIDATE_KEY_COLUMNS",
    "SourcePlayerName",
    "add_sackmann_match_key",
    "add_unmatched_diagnostics",
    "attach_tournament_ids",
    "build_enriched_matches",
    "build_linkage_summary",
    "build_manual_links",
    "build_manual_rank_and_name_links",
    "build_match_crosswalk",
    "build_name_pair_links",
    "build_rank_and_name_links",
    "build_rank_links",
    "classify_name_pair_candidates",
    "classify_rank_candidates",
    "finalize_link_status",
    "generate_name_pair_candidates",
    "generate_rank_candidates",
    "linkage_summary",
    "normalize_name",
    "parse_tennis_data_name",
    "player_name_compatible",
    "tournament_linkage_summary",
]
