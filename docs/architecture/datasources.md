# Component: `datasources`

[← Back to architecture overview](README.md)

## Responsibility

Isolates the source-specific mechanics of talking to one external data
provider: building requests, handling that provider's quirks (auth,
pagination, file formats, retries), and returning data in its **original,
unmodified shape**. Datasource clients do not clean, rename, or validate —
that is `handler`'s job.

## Inputs

- Each provider's own transport (HTTP endpoints, file downloads, etc.).
- Client-level settings from `config` (timeouts, retry counts).

## Outputs

- Raw `pandas.DataFrame`s (or equivalent) with the provider's original
  column names/shapes — no renaming or dtype normalization beyond what the
  parser itself does.

## Dependencies

- External: `requests`, `urllib3` (retry adapters), `pandas`.
- Internal: `config` (for client defaults/settings). Depended on by
  `workflows` (and, for Sackmann, called directly — see below).

## Sub-packages

| Path | Provider | Status |
|---|---|---|
| `datasources/tennis_data_uk/` | [Tennis-Data.co.uk](http://www.tennis-data.co.uk/alldata.php) | Implemented; wired into `handler`/`workflows`/`loader`. |
| `datasources/sackmann/` | Sackmann tennis archive (via a GitHub mirror) | Client + its own cleaning helpers exist (`atp.py`/`wta.py`/`cleaning.py`), but are **not** wired into `handler`/`workflows`/`loader` — see the open question below. |
| `datasources/tennis_is_my_life/` | stats.tennismylife.org | Client only (`client.py`: `list_files`/`read_csv`). No cleaning, checkpointing, or workflow layer yet. |

### `datasources/tennis_data_uk/`

| Module | Purpose |
|---|---|
| `client.py` | `TennisDataUKClient` — downloads one season's xls/xlsx and returns it as a raw `DataFrame`, untouched. Defines the `Tour` enum (`atp`/`wta`). |
| `checkpoint.py` | Stage-2 raw checkpoint: `raw_checkpoint_path()`, `fetch_and_checkpoint()`. Persists the client's output to disk byte-for-byte, with a sanity check (`_check_tour_column`) that the downloaded file actually matches the requested tour, and a schema-drift warning (`_warn_on_schema_drift`) if the column set changes between runs. |

### `datasources/sackmann/`

| Module | Purpose |
|---|---|
| `client.py` | `SackmannClient` — downloads one season's match file from the archive mirror. |
| `atp.py` / `wta.py` | `load_year()` / `load_years()` — download + optionally clean one or more seasons in one call. |
| `cleaning.py` | `clean_matches()` — cleaning logic local to this datasource. |

> TODO: Confirm whether `datasources/sackmann` is meant to stay a
> self-contained mini-pipeline (client + cleaning in one place), or whether
> its cleaning logic should eventually move into `handler/` and be
> orchestrated by `workflows/`, matching the Tennis-Data UK layout.

### `datasources/tennis_is_my_life/`

> TODO: Confirm whether this source is actively planned for a
> `handler`/`workflows`/`loader` integration, or is exploratory/unused
> for now.

## Implementation

Retries for HTTP clients use `urllib3.util.Retry` via `requests`'
`HTTPAdapter`, configured from `config`'s `ApiConfig` /
`TennisDataUKConfig` defaults.
