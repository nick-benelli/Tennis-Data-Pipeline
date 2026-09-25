# Component: `handler`

[← Back to architecture overview](README.md)

## Responsibility

Turns a raw `DataFrame` (as produced by `datasources`) into the canonical,
analysis-ready dataset: dtype coercion, known-issue fixes, structural
validation, renaming to the canonical schema, and data-quality reporting.
`handler` never does I/O (no network calls, no reading/writing checkpoint
files) or orchestration — that is `workflows`'s job.

## Inputs

- A raw `DataFrame` in the source's original column names/dtypes (from a
  `datasources` client, or reloaded from a raw checkpoint by `workflows`).

## Outputs

- A cleaned `DataFrame` in the canonical schema (renamed columns, coerced
  dtypes, provenance/key columns added).
- Data-quality artifacts: a quality report `DataFrame` and a list of
  structural inconsistencies for manual review.
- Raises on unrecoverable structural problems (e.g. reused tournament IDs)
  rather than silently producing bad data.

## Dependencies

- External: `pandas`.
- Internal: none beyond `pandas`. Depended on by `workflows.uk`,
  `workflows.sackmann`, and `workflows.wta_api` (each supplies the raw
  input and persists the output for its own source).

## Sub-packages

`handler/uk/` is the only sub-package with a full match-level clean/validate
pipeline. `handler/sackmann/` and `handler/wta_api/` are much thinner —
each holds only a `tournaments.py` that derives a tournament-summary table
(no match-level cleaning; Sackmann's match-level dtype coercion lives in
`datasources.sackmann.cleaning` instead, and the WTA-tournaments-API source
is already one row per tournament with nothing to aggregate).

| Path | Purpose |
|---|---|
| `handler/uk/cleaner/` | Per-tour cleaning: dtype loading, known-fix application, canonical renaming, quality reporting, tournament-table building. |
| `handler/uk/validator/` | Cross-cutting structural checks (currently: tournament-attribute consistency). |
| `handler/sackmann/tournaments.py` | `build_sackmann_tournament_table()` — reuses the tour-agnostic `handler.uk.cleaner.tournaments.build_tournament_table` aggregator directly (that function was never UK-specific despite its location) against Sackmann match data; infers `match_status` from the free-text `score` column. See [sackmann-fetch.md](../pipelines/sackmann-fetch.md#5-downstream-consumer-the-tournament-table). |
| `handler/wta_api/tournaments.py` | `build_wta_api_tournament_table()` — no aggregation needed (the API already returns one row per tournament); renames `tournament_group_id` → `official_tournament_id`, tags `tour="wta"`, parses dates, dedupes. See [wta-api-tournaments.md](../pipelines/wta-api-tournaments.md#2-cleantype-build_wta_api_tournament_table). |

### `handler/uk/cleaner/`

| Module | Purpose |
|---|---|
| `common.py` | Tour-agnostic helpers shared by ATP/WTA: `slugify`, `normalize_key_value`, `add_source_event_key`, `assign_round_codes`, `add_source_match_key`, `fix_bad_odds`, `check_tournament_consistency`, `check_reused_tournament_ids`. |
| `atp.py` / `atp_cols.py` | ATP-specific loading (`load_raw_atp_csv`), key/round assignment, known-fix application, validation, and the raw→canonical column map. |
| `wta.py` / `wta_cols.py` | WTA counterparts to the above. |
| `known_fixes/` | Registry of one-off, hand-verified corrections to specific matches (`_shared.py`: `MatchFix` dataclass + `apply_match_fixes()`; `atp.py`/`wta.py`: the actual fix list per tour). Each fix must match exactly one row or it is treated as a bug. |
| `quality.py` | `build_uk_quality_report()` / `update_quality_report()` — builds and upserts the shared ATP+WTA data-quality report. |
| `tournaments.py` | `build_tournament_table()` — aggregates match rows into one row per tournament. |

### `handler/uk/validator/`

| Module | Purpose |
|---|---|
| `tournaments.py` | `find_uk_inconsistent_tournaments()` — flags tournaments whose attributes (surface, series, court, etc.) aren't consistent across all their rows. |

## Implementation

See [Tennis-Data UK: data flow](../data-sources/tennis-data-uk/data-flow.md)
for how these functions are chained together for one concrete source, and
[docs/data-sources/tennis-data-uk/pipeline-plan.md](../data-sources/tennis-data-uk/pipeline-plan.md)
for the design rationale (canonical schema, known-fix registry format).

The generic aggregator (`handler.uk.cleaner.tournaments.build_tournament_table`)
being reused directly by `handler.sackmann.tournaments` — despite living
under the `uk` package — answers what was previously an open question here:
new sources are not expected to duplicate this logic, only supply their own
column-name bindings.
