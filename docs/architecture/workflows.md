# Component: `workflows`

[← Back to architecture overview](README.md)

## Responsibility

Orchestrates `datasources` + `handler` + checkpoint I/O into complete,
callable pipelines: "fetch this season", "clean this season", "do the whole
thing end-to-end on a schedule". `workflows` is the only layer that reads or
writes checkpoint files on disk; it owns the raw/clean directory layout and
naming conventions (via `config`). `workflows.mapper` extends this same role
to the cross-source pipelines: it loads other sources' already-built
tournament/match tables, calls `mapper`'s pure matching logic, and persists
the result under `data/mapping/`/`data/linked/`.

## Inputs

- A tour + year (or range of years) to process.
- Configuration (checkpoint directory layout, filenames) from `config`.

## Outputs

- Raw and clean checkpoint CSVs written to `data/raw/` / `data/clean/`.
- Cross-source tournament-id crosswalk/source-links CSVs (`data/mapping/`)
  and per-tour/year match-linkage CSVs (`data/linked/`), from
  `workflows.mapper`.
- Per-run result objects summarizing what succeeded/failed
  (`CleanYearResult`, `YearUpdateResult`, `SeasonUpdateReport`), used by
  scripts/CI to decide whether to fail the run.

## Dependencies

- Internal: `datasources` (fetch), `handler` (clean/validate), `config`
  (paths and settings), and — for `workflows.mapper` — `mapper` (pure
  matching logic) plus `workflows.uk`/`workflows.sackmann`/`workflows.wta_api`
  (the tournament tables it matches). Depended on by `scripts/` (CLI entry
  points) and, indirectly, `loader` (reads what `workflows` writes).

## Sub-packages

`workflows/uk/` has the deepest pipeline (fetch → clean → tournament table
→ scheduled update). `workflows/sackmann/` and `workflows/wta_api/` each
only build a tournament-summary table (Sackmann has no fetch/clean stage of
its own — it calls `datasources.sackmann` live; WTA-API's own fetch
checkpoint isn't what feeds its tournament table, which also re-fetches
live). `workflows/mapper/` is different in kind: it doesn't fetch or clean
anything, it consumes other sources' already-built tournament/match tables
to produce the cross-source id crosswalk and match-level linkage.

| Module | Purpose |
|---|---|
| `workflows/uk/fetch.py` | Stage 1-2: `fetch_and_checkpoint_year()` / `fetch_and_checkpoint_years()` (download + persist raw checkpoint), `load_raw_year()` (reload a raw checkpoint, no cleaning). |
| `workflows/uk/clean.py` | Stage 3-4: `clean_year()` / `clean_years()` (load a raw checkpoint, clean it, write the clean checkpoint), `clean_checkpoint_path()` / `quality_report_path()`. |
| `workflows/uk/tournaments.py` | Builds/updates the tournament-summary table: `build_uk_tournaments()`, `tournament_table_path()`, `tournament_inconsistencies_path()`. |
| `workflows/uk/update.py` | Stage 6: `update_current_season()` — best-effort fetch + clean + tournament rebuild for one or more tour/years, safe to run unattended. |
| `workflows/uk/__init__.py` | Flat re-export of the above so callers only need `from tennis_data_pipeline.workflows.uk import ...`. |
| `workflows/sackmann/tournaments.py` | `build_sackmann_tournaments()` — downloads each requested season live via `datasources.sackmann`, aggregates via `handler.sackmann.tournaments`, upserts into `data/clean/sackmann/<tour>/tournaments/`. See [sackmann-fetch.md](../pipelines/sackmann-fetch.md). |
| `workflows/wta_api/fetch.py` | Raw checkpoint fetch (mirrors `workflows/uk/fetch.py`'s shape) — see [wta-api-fetch.md](../pipelines/wta-api-fetch.md). |
| `workflows/wta_api/tournaments.py` | `build_wta_api_tournaments()` — fetches live (not from the raw checkpoint), cleans via `handler.wta_api.tournaments`, upserts into `data/clean/wta_api/tournaments/`. See [wta-api-tournaments.md](../pipelines/wta-api-tournaments.md). |
| `workflows/mapper/tournaments.py` | `build_tournament_mapping()` — matches UK/Sackmann (+ WTA-API backfill) tournament tables via `mapper.tournaments`, upserts the crosswalk + source-links CSVs under `data/mapping/tournaments/`. See [tournament-matching.md](../pipelines/tournament-matching.md). |
| `workflows/mapper/matches/uk_sackmann.py` | `build_match_links()` — links individual UK↔Sackmann matches via `mapper.matches.uk_sackmann`, writes five CSVs per tour/year under `data/linked/{tour}/{year}/`. See [match-linking.md](../pipelines/match-linking.md). |
| `workflows/_csv_upsert.py` | Shared `upsert_csv()` helper used by every upsert-based workflow above (UK/Sackmann/WTA-API tournament tables, mapping crosswalk). |

## Implementation

`workflows/uk/update.py` backs `scripts/uk/weekly_update.py`, the scheduled
refresh entry point. See
[Tennis-Data UK: data flow](../data-sources/tennis-data-uk/data-flow.md) for
the full stage-by-stage call chain.
