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

## Outputs

- `DataFrame`s in the canonical schema, with dtypes matching what `handler`
  originally produced (categoricals, nullable ints, parsed dates).

## Dependencies

- External: `pandas`.
- Internal: `config` (path resolution), `handler.uk.cleaner.common` (shared
  dtype/column lists, so the loader and cleaner can't silently drift apart).

## Sub-packages

Currently `loader` only has a `uk.py` module (Tennis-Data UK).

| Function | Purpose |
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
`handler/uk/cleaner/`.

> TODO: Confirm whether `loader` is expected to grow a package per data
> source (mirroring `datasources`/`handler`/`workflows`), once a second
> source has a full clean/checkpoint pipeline.
