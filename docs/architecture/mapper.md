# Component: `mapper`

[← Back to architecture overview](README.md)

## Responsibility

Cross-source matching logic: giving the same real-world tournament (or
match) instance from two or more independent data sources one shared
identity. `mapper` is pure — no file I/O, no network calls — it only scores
and pairs candidates over already-loaded `DataFrame`s. Persisting its
output (and loading its inputs) is `workflows.mapper`'s job; typed reload of
its output is `loader`'s job (`loader/mapper.py`, `loader/linked.py`).

## Inputs

- Already-built tournament-summary tables from `handler.uk.cleaner.tournaments`,
  `handler.sackmann.tournaments`, and `handler.wta_api.tournaments`
  (`mapper.tournaments`).
- Already-cleaned match-level `DataFrame`s from Tennis-Data UK
  (`loader.uk`) and Sackmann (`datasources.sackmann`, live), plus the
  tournament-id crosswalk `mapper.tournaments` produced
  (`mapper.matches.uk_sackmann`).
- Hand-maintained manual-override tables (`manual_matches` for tournaments,
  `manual_links` for matches) — always resolved first/pre-seeded so an
  automatic rerun can never reconsider or overwrite a human correction.

## Outputs

- `mapper.tournaments`: a `TournamentMatchResult` (`link_df` + a weak-match
  `review_df`), plus pure builder functions for a growable
  `location -> official_tournament_id` crosswalk and a long/tidy
  per-source id-links table.
- `mapper.matches.uk_sackmann`: `accepted`/`ambiguous`/`unmatched` match-level
  link tables, reshaped by `outputs.py` into a compact crosswalk, an
  "enriched" UK-plus-linkage table, a one-row coverage summary, and two
  review tables.

## Dependencies

- External: `pandas`, `difflib` (name similarity), `unicodedata` (accent
  stripping).
- Internal: none — pure logic, no dependency on `config`, `datasources`,
  `handler`, or `workflows`. Depended on by `workflows.mapper` (which
  supplies inputs and persists outputs) and `loader.mapper`/`loader.linked`
  (typed reload of the persisted CSVs).

## Sub-packages

| Path | Purpose | Detail |
|---|---|---|
| `mapper/tournaments.py` | Tournament-id matching: `match_uk_to_sackmann_tourneys`, `extract_official_tournament_id`, `match_sackmann_to_wta_api_tourneys` (WTA-only backfill), `build_location_crosswalk`, `build_source_links`. | [tournament-matching.md](../pipelines/tournament-matching.md) |
| `mapper/matches/uk_sackmann/` | Match-level linking: `schema.py` (constants), `tournament_ids.py` (id attachment), `names.py` (deterministic name compatibility), `pass0.py`/`pass1.py`/`pass2.py` (manual/rank/name-pair passes), `pipeline.py` (combines passes), `checker.py` (coverage diagnostics), `outputs.py` (output-table shaping). Re-exported flat from `mapper/matches/__init__.py` — always import from `mapper.matches`, never the deep `.uk_sackmann` path. | [match-linking.md](../pipelines/match-linking.md) |

## Implementation

Both sub-packages follow the same shape: a scoring/matching function, a
greedy or precedence-based acceptance rule (never force a pair below a
score floor; ambiguous candidates are kept for review, not dropped), and a
hand-maintained manual-override mechanism resolved before anything
algorithmic runs. Neither sub-package touches a second data source pair
today — tournament matching covers UK + Sackmann + (WTA-only) the
WTA-tournaments-API backfill; match-level linking covers only UK + Sackmann.
A future third source would get its own sibling submodule
(`mapper/matches/<other_pair>/`), per `mapper/matches/__init__.py`'s own
docstring.

## Known Limitations

- Greedy assignment (both sub-packages) is not globally optimal — see each
  pipeline doc's own "Known limitations" section for the specific failure
  modes this has caused in practice (e.g. the 2022 WTA Melbourne Summer Set
  1/2 id swap).
- Match-level linking has a hard dependency on tournament matching already
  being built for the tour/year in question — see the prerequisite note at
  the top of [match-linking.md](../pipelines/match-linking.md).
