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
| `datasources/tennis_data_uk/` | [Tennis-Data.co.uk](http://www.tennis-data.co.uk/alldata.php) | Implemented; wired into `handler`/`workflows`/`loader` end to end, including a full match-level raw+clean checkpoint. |
| `datasources/sackmann/` | Sackmann tennis archive (via a GitHub mirror) | Client + its own cleaning helpers (`atp.py`/`wta.py`/`cleaning.py`) are called live by `workflows.sackmann.tournaments` to build a tournament-summary table (see [sackmann-fetch.md](../pipelines/sackmann-fetch.md)) and by the cross-source `mapper`/match-linking pipelines — but there is still no match-level raw/clean checkpoint under `data/raw/`/`data/clean/sackmann/`; every call re-downloads from GitHub. |
| `datasources/wta/` | WTA tournaments API (`api.wtatennis.com`) | Implemented; `WtaApiClient` (paginated fetch) + `cleaner.flatten_tournament` + `checkpoint` are wired into `workflows.wta_api`/`handler.wta_api` to produce a raw checkpoint and a clean tournament table — see [wta-api-fetch.md](../pipelines/wta-api-fetch.md) / [wta-api-tournaments.md](../pipelines/wta-api-tournaments.md). WTA-only; no ATP equivalent exists. |

### `datasources/tennis_data_uk/`

| Module | Purpose |
|---|---|
| `client.py` | `TennisDataUKClient` — downloads one season's xls/xlsx and returns it as a raw `DataFrame`, untouched. Defines the `Tour` enum (`atp`/`wta`). |
| `checkpoint.py` | Stage-2 raw checkpoint: `raw_checkpoint_path()`, `fetch_and_checkpoint()`. Persists the client's output to disk byte-for-byte, with a sanity check (`_check_tour_column`) that the downloaded file actually matches the requested tour, and a schema-drift warning (`_warn_on_schema_drift`) if the column set changes between runs. |

### `datasources/sackmann/`

| Module | Purpose |
|---|---|
| `client.py` | `SackmannClient` — downloads one season's match file from the archive mirror. |
| `atp.py` / `wta.py` | `load_year()` / `load_years()` — download + optionally clean one or more seasons in one call, plus tier-specific variants (qual/challenger, futures, qual+ITF, ATP doubles). |
| `cleaning.py` | `clean_matches()` / `clean_doubles_matches()` — dtype coercion + `canonical_match_key` derivation, local to this datasource. |
| `schema.py` | File-naming templates and the two column/dtype layouts (singles vs. ATP doubles). |

This mini-pipeline (client + cleaning in one subpackage, not split across
`handler`/`workflows`) is the answer to what was previously an open
question here: `workflows.sackmann.tournaments.build_sackmann_tournaments`
and the cross-source `mapper`/match-linking pipelines both call
`datasources.sackmann.{atp,wta}.load_year(s)` directly, live, every run —
see [sackmann-fetch.md](../pipelines/sackmann-fetch.md) for the full
call chain and its known limitations (no checkpoint, no known-fix registry).

### `datasources/wta/`

| Module | Purpose |
|---|---|
| `client.py` | `WtaApiClient` — pages through `GET /tennis/tournaments/` (server-capped at 100 entries/page), raises `WtaApiDownloadError` on failure. |
| `cleaner.py` | `flatten_tournament()` — flattens one raw tournament JSON entry into a row (this determines the raw checkpoint's column set). |
| `checkpoint.py` | Persists a season's flattened `DataFrame` to disk unmodified; warns (doesn't raise) on schema drift. |

See [wta-api-fetch.md](../pipelines/wta-api-fetch.md) for the pagination
mechanics and the TLS-verification-disabled caveat.

## Implementation

Retries for HTTP clients use `urllib3.util.Retry` via `requests`'
`HTTPAdapter`, configured from `config`'s `ApiConfig` /
`TennisDataUKConfig` / `SackmannConfig` / `WtaApiConfig` defaults.
