# Component: `loader`

[← Back to architecture overview](README.md)

## Responsibility

Reads previously-cleaned checkpoint CSVs back into memory with their
intended dtypes restored. Writing a cleaned `DataFrame` to CSV and reading
it back with plain `pandas.read_csv` loses categoricals, nullable ints, and
parsed dates — `loader` exists specifically to undo that round-trip loss.
It performs no cleaning or validation of its own.

## Inputs

- Clean checkpoint CSVs written by `workflows` (paths resolved via
  `config`'s `settings.paths.clean`).
- Cross-source mapping/linkage CSVs written by `workflows.mapper` (paths
  resolved via `settings.paths.mapping` / `settings.paths.linked`).

## Outputs

- `DataFrame`s in the canonical schema, with dtypes matching what `handler`
  originally produced (categoricals, nullable ints, parsed dates).
- `DataFrame`s from `data/mapping/`/`data/linked/` with
  `official_tournament_id` restored to nullable `Int64` (a plain
  `pd.read_csv` round-trip otherwise turns any column with a missing value
  into `float64`, e.g. `301` read back as `301.0`).

## Dependencies

- External: `pandas`.
- Internal: `config` (path resolution), `handler.uk.cleaner.common` (shared
  dtype/column lists, so the loader and cleaner can't silently drift
  apart), `mapper.matches` / `mapper.tournaments` (shared column-list
  constants for the mapping/linkage loaders).

## Sub-packages

| Module | Purpose |
|---|---|
| `loader/uk.py` | Tennis-Data UK clean-checkpoint reload (see function table below). |
| `loader/mapper.py` | Reload for `mapper.tournaments`' crosswalk/source-links CSVs (`data/mapping/tournaments/`) and `mapper.matches`' manual-link overrides (`data/mapping/matches/`), with `official_tournament_id` restored to `Int64`. |
| `loader/linked.py` | Path helpers for `mapper.matches.uk_sackmann`'s per-year formalized outputs (`data/linked/{tour}/{year}/`) — crosswalk, enriched matches, linkage summary. |
| `loader/tournaments.py` | Currently an empty placeholder (docstring only) — not imported anywhere in the codebase today. |

| Function (`loader/uk.py`) | Purpose |
|---|---|
| `load_clean_uk_data(path, tour)` | Load one clean checkpoint file with correct dtypes. |
| `load_clean_uk_year(tour, year, clean_dir=None)` | Resolve the path for one tour/year and load it. |
| `load_clean_uk_data_range(...)` | Load and concatenate multiple years for one tour. |
| `load_clean_uk_combined(...)` | Load and concatenate both tours together. |
| `load_clean_uk_atp_data(path)` | Convenience wrapper for ATP-only loading. |

## Implementation

Column groupings (`CATEGORY_COLS`, `BOOLEAN_COLS`, `STRING_COLS`,
`DATE_COLS`, nullable-int columns) are defined at the top of `loader/uk.py`
and must stay in sync with the canonical schema produced by
`handler/uk/cleaner/`. `loader/mapper.py`/`loader/linked.py` have no
dtype-restoring counterpart for Sackmann or WTA-API data — those sources'
workflows don't produce a dtype-typed checkpoint to reload in the first
place (see [datasources.md](datasources.md)).
