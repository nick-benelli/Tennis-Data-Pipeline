# Component: `config`

[← Back to architecture overview](README.md)

## Responsibility

Loads, validates, and exposes application configuration to the rest of the
package: filesystem paths, logging, generic HTTP client defaults, and
per-data-source settings. Every other subpackage reads settings through this
component rather than hard-coding values.

## Inputs

- `configs/config.yaml` (default config file; path resolution documented in
  [Configuration](README.md#configuration)).
- Environment variables referenced by `${VAR}` / `${VAR:default}` placeholders
  inside `config.yaml`.
- `TENNIS_DATA_PIPELINE_CONFIG` (override the config file path) and
  `TENNIS_DATA_PIPELINE_PROJECT_DIR` (override the detected project root).

## Outputs

- A validated `AppConfig` (pydantic) instance, accessed via the lazy
  `settings` proxy or `get_settings()`.
- Resolved, absolute `Path` objects for the raw/clean/archive/mapping/linked
  data directories (`settings.paths.raw` / `.clean` / `.archive` / `.mapping`
  / `.linked`).

## Dependencies

- External: `pydantic`, `pydantic-settings`, `pyaml`, `python-dotenv`.
- Internal: none — this is a leaf component. Every other subpackage
  (`datasources`, `handler`, `loader`, `workflows`, `mapper`) depends on it.

## Implementation

| Module | Purpose |
|---|---|
| `config/loader.py` | Resolves the config file path, substitutes env vars (`_substitute_env_vars`), loads/caches the `AppConfig` (`get_settings`, `clear_config_cache`), exposes the lazy `settings` proxy (`_SettingsProxy`). |
| `config/schemas/` | A package of pydantic models, one file per section, re-exported from `schemas/__init__.py`: `app.py` (`AppConfig`, the root model), `api.py` (`ApiConfig`), `logging.py` (`LoggingConfig`), `paths.py` (`PathsConfig`), `uk.py` (`TennisDataUKConfig`), `sackmann.py` (`SackmannConfig`), `wta_api.py` (`WtaApiConfig`), `mapping.py` (`MappingConfig`), `linked.py` (`LinkedConfig`), `base.py` (shared `StrictModel` base). All reject unknown keys (`StrictModel`, `extra="forbid"`). |
| `config/paths.py` | `PACKAGE_DIR` / `PROJECT_DIR` constants used to auto-detect the repo root. |

Each data source that persists its own output gets its own `*Config` model
+ `configs/config.yaml` section, mirroring `TennisDataUKConfig`: `sackmann`
(client + tournament-table settings), `wta_api` (client + tournament-table
settings), `mapping` (cross-source tournament-id crosswalk paths/filenames,
`min_match_score`), `linked` (match-linkage output paths/filenames). This
answers the config doc's original open question — yes, a new integrated
source is expected to add its own config section this way.

> Note: `string.Template.safe_substitute` does **not** support the
> `${VAR:default}` syntax used in `config.yaml` — `loader.py` implements its
> own regex-based substitution (`_ENV_VAR_PATTERN`) instead. See
> `/memories/repo/config-subpackage.md` for the history of this.
