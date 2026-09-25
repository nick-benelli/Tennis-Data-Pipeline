"""Cross-source match-level linking: Tennis-Data UK <-> Sackmann.

Pure functions over already-clean match-level `DataFrame`s - no file I/O here
(see `workflows.mapper` for that layer, following the `mapper.tournaments`
precedent).

Pass 0 (hand-maintained manual overrides, `build_manual_links`) runs first:
a `(source_match_key, canonical_match_key)` table resolved straight to
accepted links and removed from both sides' pools *before* Pass 1/2 run - so
a manually-confirmed pair can never be reconsidered, or wrongly reclaimed for
a different match, by either algorithmic pass. Meant for the small number of
matches with no algorithmic path to a link at all (e.g. no rank data, no
name-pair signal, or a genuinely unmappable exhibition event).

Pass 1 (tournament-blocked exact rank pair, `build_rank_links`):

    UK match row                    Sackmann match row
         |                                 |
    official_tournament_id  <----(tournament_mapper)---->  official_tournament_id
         |                                 |
         +--------- year, tour, winner_rank, loser_rank ---+
                            |
                    candidate match
                            |
              exactly one on both sides?
                    /              \\
                 yes                no
                  |                  |
          accepted link      ambiguous candidate

Rows that never produce a Pass-1 candidate (missing tournament id, missing
rank, or no counterpart) fall out as unmatched.

Pass 2 (tournament + round blocked, deterministic winner/loser name pair,
`build_name_pair_links`) picks up from there: for the residual UK rows Pass 1
couldn't place, and the residual Sackmann rows Pass 1 didn't consume, it tries
(`year`, `tour`, `official_tournament_id`, `round`) as a hard block, then a
deterministic (not fuzzy) surname + given-name-initial check on the
winner/loser pair, with orientation preserved - see `player_name_compatible`.
This is meant to catch rows where a rank is missing or disagrees between
sources but the identities are otherwise unambiguous.

There is no player-name-alias *learning* here (no cross-match memory of "this
UK spelling always maps to this Sackmann id") - each Pass-2 decision is made
fresh from the two names in front of it, scoped to the same tournament+round.
`build_rank_and_name_links` runs both algorithmic passes and combines the
results; `build_manual_rank_and_name_links` runs Pass 0 first and then
`build_rank_and_name_links` on the residual - see
`docs/My-Notes/link_td_sackmann.py` / `Link-UK-Sackmann.ipynb` for the
original exploration and the passes beyond this one.

Split across submodules (this file is the public API surface - import from
here, not from a submodule directly):

- `schema`: shared constants (match-method names, crosswalk column lists).
- `tournament_ids`: `attach_tournament_ids` - the id-attachment merge.
- `names`: deterministic (non-fuzzy) player-name parsing/compatibility.
- `pass0`: hand-maintained manual-override linking (`build_manual_links`).
- `pass1`: tournament-blocked exact rank-pair linking (`build_rank_links`).
- `pass2`: tournament+round blocked name-pair linking (`build_name_pair_links`).
- `pipeline`: `build_rank_and_name_links`/`build_manual_rank_and_name_links` -
  runs the passes and combines them.
- `checker`: coverage/linkage diagnostics (`tournament_linkage_summary`,
  `linkage_summary`) - reporting only, no linking logic.
- `outputs`: build the formalized per-year output tables (crosswalk,
  enriched matches, finalized ambiguous/unmatched, linkage summary) - see
  `workflows.mapper.matches.uk_sackmann` for the layer that writes them to CSV.
"""

from __future__ import annotations

from .checker import linkage_summary, tournament_linkage_summary
from .names import SourcePlayerName, normalize_name, parse_tennis_data_name, player_name_compatible
from .outputs import (
    ENRICHED_LINKAGE_BLOCK_COLUMNS,
    LINKAGE_SUMMARY_COLUMNS,
    MATCH_CROSSWALK_COLUMNS,
    add_unmatched_diagnostics,
    build_enriched_matches,
    build_linkage_summary,
    build_match_crosswalk,
    finalize_link_status,
)
from .pass0 import build_manual_links
from .pass1 import (
    add_sackmann_match_key,
    build_rank_links,
    classify_rank_candidates,
    generate_rank_candidates,
)
from .pass2 import build_name_pair_links, classify_name_pair_candidates, generate_name_pair_candidates
from .pipeline import build_manual_rank_and_name_links, build_rank_and_name_links
from .schema import (
    CROSSWALK_COLUMNS,
    MANUAL_LINKS_COLUMNS,
    MATCH_METHOD_MANUAL,
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
    NAME_PAIR_CROSSWALK_COLUMNS,
    NAME_PAIR_KEY_COLUMNS,
    RANK_CANDIDATE_KEY_COLUMNS,
)
from .tournament_ids import attach_tournament_ids

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
