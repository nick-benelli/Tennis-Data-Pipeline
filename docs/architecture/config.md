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
- Resolved, absolute `Path` objects for the raw/clean/archive data
  directories (`settings.paths.raw` / `.clean` / `.archive`).

## Dependencies

- External: `pydantic`, `pydantic-settings`, `pyaml`, `python-dotenv`.
- Internal: none — this is a leaf component. Every other subpackage
  (`datasources`, `handler`, `loader`, `workflows`) depends on it.

## Implementation

| Module | Purpose |
|---|---|
| `config/loader.py` | Resolves the config file path, substitutes env vars (`_substitute_env_vars`), loads/caches the `AppConfig` (`get_settings`, `clear_config_cache`), exposes the lazy `settings` proxy (`_SettingsProxy`). |
| `config/schemas.py` | Pydantic models: `AppConfig`, `ApiConfig`, `LoggingConfig`, `PathsConfig`, `TennisDataUKConfig`. All reject unknown keys (`StrictModel`, `extra="forbid"`). |
| `config/paths.py` | `PACKAGE_DIR` / `PROJECT_DIR` constants used to auto-detect the repo root. |

> Note: `string.Template.safe_substitute` does **not** support the
> `${VAR:default}` syntax used in `config.yaml` — `loader.py` implements its
> own regex-based substitution (`_ENV_VAR_PATTERN`) instead. See
> `/memories/repo/config-subpackage.md` for the history of this.

> TODO: Confirm whether new data sources are expected to add their own
> `*Config` model + section (mirroring `TennisDataUKConfig`), or whether a
> more generic per-source config shape is planned.
