# Scripts

[← Architecture overview](../architecture/README.md) · [Pipelines overview](../pipelines/README.md)

`scripts/` holds thin CLI entry points around `workflows` (see
[architecture: Repository Structure](../architecture/README.md#repository-structure)).
This page is a complete CLI reference for every script: parameters and
example invocations. For *why* a script does what it does (the pipeline
behind it), follow the linked doc under [docs/pipelines/](../pipelines/README.md).

Every script also accepts `--help` for the same parameter list live from
the terminal — this page exists so you don't have to run each one just to
see its options.

## `scripts/uk/` — Tennis-Data UK

### `call_tennis_data_uk.py`

Downloads one or more seasons from tennis-data.co.uk and writes the Stage-2
raw checkpoint. See [Tennis-Data UK: Fetch](../pipelines/tennis-data-uk-fetch.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `--tour` | `{atp, wta}` | required | Tour to download. |
| `--year` | int | optional | Single season to fetch. |
| `--start-year` | int | optional (default: `2000` ATP / `2007` WTA) | First season of a range. |
| `--end-year` | int | optional (default: `--year`, else current year) | Last season of a range. |
| `--write` / `--no-write` | flag | `--write` (default `True`) | Write the checkpoint, or dry-run (download + report row counts only). |

```bash
python scripts/uk/call_tennis_data_uk.py --tour atp --year 2024
python scripts/uk/call_tennis_data_uk.py --tour wta --start-year 2020 --end-year 2024
python scripts/uk/call_tennis_data_uk.py --tour atp                     # defaults to the current season
python scripts/uk/call_tennis_data_uk.py --tour atp --year 2024 --no-write
```

### `clean_uk_data.py`

Cleans Stage-2 raw checkpoints into the Stage-4 canonical-schema dataset. See
[Tennis-Data UK: Clean](../pipelines/tennis-data-uk-clean.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}` | required | Tour to clean. |
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2022 2019 2010-2015`. |
| `--raw-dir` | path | optional (config-driven) | Override the Stage-2 raw checkpoint directory. |
| `--clean-dir` | path | optional (config-driven) | Override the Stage-4 clean checkpoint directory. |
| `--fail-fast` | flag | off | Stop at the first year that fails instead of processing the rest. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/uk/clean_uk_data.py --tour atp 2022
python scripts/uk/clean_uk_data.py --tour wta 2019 2015 2013
python scripts/uk/clean_uk_data.py --tour atp 2010-2023
python scripts/uk/clean_uk_data.py --tour wta 2007-2015 2020-2023 --verbose
```

### `weekly_update.py`

Unattended-safe fetch + clean + tournament-table rebuild, meant to run on a
schedule. Wraps the [fetch](../pipelines/tennis-data-uk-fetch.md) and
[clean](../pipelines/tennis-data-uk-clean.md) pipelines with best-effort,
per-tour/year fault isolation (not yet documented as its own dedicated
pipeline page).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}`, repeatable | optional (default: both tours) | Tour(s) to update, e.g. `-t atp -t wta`. |
| `--years` | int, one or more | optional (default: current year + previous year) | Years to update. |
| `--raw-dir` | path | optional (config-driven) | Override the Stage-2 raw checkpoint directory. |
| `--clean-dir` | path | optional (config-driven) | Override the Stage-4 clean checkpoint directory. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/uk/weekly_update.py
python scripts/uk/weekly_update.py --tour atp
python scripts/uk/weekly_update.py --years 2025 2026
python scripts/uk/weekly_update.py --verbose
```

Exit code `1` means at least one tour/year needs attention (a clean
failure, not just a not-yet-published season) — see the pipeline doc for
the best-effort-per-year semantics.

### `build_uk_tournaments.py`

Builds/updates the UK tournament-summary table from clean checkpoints. See
[Tennis-Data UK: Tournament Table](../pipelines/tennis-data-uk-tournaments.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}` | required | Tour to build tournaments for. |
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2022 2019 2010-2015`. |
| `--clean-dir` | path | optional (config-driven) | Override the Stage-4 clean checkpoint directory (input). |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/uk/build_uk_tournaments.py --tour atp 2022
python scripts/uk/build_uk_tournaments.py --tour wta 2019 2015 2013
python scripts/uk/build_uk_tournaments.py --tour atp 2010-2023
```

Requires the requested years to already be cleaned (`clean_uk_data.py`
first) — a year without a clean checkpoint is skipped with a warning.

## `scripts/sackmann/` — Sackmann archive

### `build_sackmann_tournaments.py`

Builds/updates the Sackmann tournament-summary table. Downloads live every
run — no local checkpoint for this source. See
[Sackmann Archive: Data Access](../pipelines/sackmann-fetch.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}` | required | Tour to build tournaments for. |
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2024 2019 2000-2015`. |
| `--clean-dir` | path | optional (config-driven) | Override the tournament-table output directory. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/sackmann/build_sackmann_tournaments.py --tour atp 2000-2024
python scripts/sackmann/build_sackmann_tournaments.py --tour wta 2019 2015 2013
python scripts/sackmann/build_sackmann_tournaments.py --tour atp 2024
```

## `scripts/wta_api/` — WTA tournaments API

### `call_wta_api.py`

Downloads one or more seasons of WTA tournaments (every level, ITF included)
and writes the raw checkpoint. See
[WTA Tournaments API: Fetch](../pipelines/wta-api-fetch.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2026 2020-2025`. |
| `--raw-dir` | path | optional (config-driven) | Override the raw checkpoint output directory. |
| `--write` / `--no-write` | flag | `--write` (default `True`) | Write the checkpoint, or dry-run (download + report row counts only). |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/wta_api/call_wta_api.py 2026
python scripts/wta_api/call_wta_api.py 2020-2026
python scripts/wta_api/call_wta_api.py 2019 2024 2026
python scripts/wta_api/call_wta_api.py 2026 --no-write
```

No `--tour` flag — this API only covers WTA.

### `build_wta_api_tournaments.py`

Builds/updates the WTA-tournaments-API tournament-summary table — the
authoritative `official_tournament_id` source used by
[tournament matching](../pipelines/tournament-matching.md). See
[WTA Tournaments API: Tournament Table](../pipelines/wta-api-tournaments.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2026 2020-2025`. |
| `--clean-dir` | path | optional (config-driven) | Override the tournament-table output directory. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/wta_api/build_wta_api_tournaments.py 2026
python scripts/wta_api/build_wta_api_tournaments.py 2020-2026
python scripts/wta_api/build_wta_api_tournaments.py 2019 2024 2026
```

## `scripts/mapper/` — Cross-source matching

### `build_tournament_mapping.py`

Matches UK ↔ Sackmann ↔ (WTA-only) WTA-API tournaments into the permanent
`official_tournament_id` crosswalk. **Requires** both tours' tournament
tables to already exist (`build_uk_tournaments.py` /
`build_sackmann_tournaments.py`, and `build_wta_api_tournaments.py` for
WTA). See
[Cross-Source Tournament Matching](../pipelines/tournament-matching.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}` | required | Tour to map. |
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2022 2019 2010-2015`. |
| `--review-threshold` | float | optional (default `0.9`) | Print matched pairs scoring below this for manual review. |
| `--uk-clean-dir` | path | optional (config-driven) | Override the UK Stage-4 clean checkpoint directory. |
| `--sackmann-clean-dir` | path | optional (config-driven) | Override the Sackmann clean checkpoint directory. |
| `--wta-api-clean-dir` | path | optional (config-driven) | Override the WTA-tournaments-API clean checkpoint directory. |
| `--mapping-dir` | path | optional (config-driven, `data/mapping`) | Override the mapping output directory. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/mapper/build_tournament_mapping.py --tour atp 2025
python scripts/mapper/build_tournament_mapping.py --tour atp 2010-2025
python scripts/mapper/build_tournament_mapping.py --tour wta 2024 2025 --review-threshold 0.95
```

A year missing either source's tournament table is skipped with a warning,
not a hard failure — exit code is `1` only if *every* requested year was
skipped/failed.

### `link_matches_uk_sackmann.py`

Links individual UK ↔ Sackmann matches (Pass 0 manual overrides, then Pass 1
rank-pair, then Pass 2 name-pair). **Requires**
[tournament matching](../pipelines/tournament-matching.md) to already be
built for the requested tour/year(s) — see
[Cross-Source Match Linking](../pipelines/match-linking.md).

| Parameter | Type | Required / Default | Description |
|---|---|---|---|
| `-t`, `--tour` | `{atp, wta}` | required | Tour to link. |
| `years` | positional, one or more | required | Years and/or ranges, e.g. `2022 2019 2010-2015`. |
| `--mapping-dir` | path | optional (config-driven, `data/mapping`) | Override the mapping directory (tournament crosswalk + manual-link overrides). |
| `--linked-dir` | path | optional (config-driven, `data/linked`) | Override the linked-output directory. |
| `--verbose` | flag | off | Enable debug logging. |

```bash
python scripts/mapper/link_matches_uk_sackmann.py --tour atp 2025
python scripts/mapper/link_matches_uk_sackmann.py --tour atp 2010-2025
python scripts/mapper/link_matches_uk_sackmann.py --tour wta 2024 2025
```

Requires that year's clean UK match CSV to already exist
(`scripts/uk/clean_uk_data.py`) — a year missing it is skipped with a
warning.

## `scripts/timl/` — Tennis Is My Life (stats.tennismylife.org)

### `timl_download_all.py`

Downloads every file listed by the TennisMyLife API into
`data/raw/tennis_my_life/`. Not yet part of a documented pipeline (client
only, no clean/workflow layer — see
[architecture: datasources](../architecture/datasources.md)).

No CLI parameters — the output directory (`OUTPUT_DIR`) is hardcoded in the
script, not config-driven or overridable via a flag.

```bash
python scripts/timl/timl_download_all.py
```

### `archive/timl_download_all.py`

Archived, pre-`TennisMyLifeClient` version of the same downloader (raw
`requests` calls against the data-files API directly). Kept for reference
only — prefer `scripts/timl/timl_download_all.py`. No CLI parameters.

```bash
python scripts/timl/archive/timl_download_all.py
```

