# Component: `workflows`

[← Back to architecture overview](README.md)

## Responsibility

Orchestrates `datasources` + `handler` + checkpoint I/O into complete,
callable pipelines: "fetch this season", "clean this season", "do the whole
thing end-to-end on a schedule". `workflows` is the only layer that reads or
writes checkpoint files on disk; it owns the raw/clean directory layout and
naming conventions (via `config`).

## Inputs

- A tour + year (or range of years) to process.
- Configuration (checkpoint directory layout, filenames) from `config`.

## Outputs

- Raw and clean checkpoint CSVs written to `data/raw/` / `data/clean/`.
- Per-run result objects summarizing what succeeded/failed
  (`CleanYearResult`, `YearUpdateResult`, `SeasonUpdateReport`), used by
  scripts/CI to decide whether to fail the run.

## Dependencies

- Internal: `datasources` (fetch), `handler` (clean/validate), `config`
  (paths and settings). Depended on by `scripts/` (CLI entry points) and,
  indirectly, `loader` (reads what `workflows` writes).

## Sub-packages

Currently `workflows` only has a `uk/` package.

| Module | Purpose |
|---|---|
| `workflows/uk/fetch.py` | Stage 1-2: `fetch_and_checkpoint_year()` / `fetch_and_checkpoint_years()` (download + persist raw checkpoint), `load_raw_year()` (reload a raw checkpoint, no cleaning). |
| `workflows/uk/clean.py` | Stage 3-4: `clean_year()` / `clean_years()` (load a raw checkpoint, clean it, write the clean checkpoint), `clean_checkpoint_path()` / `quality_report_path()`. |
| `workflows/uk/tournaments.py` | Builds/updates the tournament-summary table: `build_uk_tournaments()`, `tournament_table_path()`, `tournament_inconsistencies_path()`. |
| `workflows/uk/update.py` | Stage 6: `update_current_season()` — best-effort fetch + clean + tournament rebuild for one or more tour/years, safe to run unattended. |
| `workflows/uk/__init__.py` | Flat re-export of the above so callers only need `from tennis_data_pipeline.workflows.uk import ...`. |

## Implementation

`workflows/uk/update.py` backs `scripts/uk/weekly_update.py`, the scheduled
refresh entry point. See
[Tennis-Data UK: data flow](../data-sources/tennis-data-uk/data-flow.md) for
the full stage-by-stage call chain.

> TODO: Confirm whether other data sources (Sackmann, Tennis Is My Life) are
> expected to get their own `workflows/<source>/` package eventually.
