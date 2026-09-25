# Pipelines

[← Architecture overview](../architecture/README.md)

This folder documents the repo's end-to-end pipelines — the *process* behind
a script, not just the CLI flags. Each doc studies the actual package code
(`src/tennis_data_pipeline/...`) and the thin script(s) that kick it off, and
answers: what does this stage actually do, in what order, and why.

Every doc follows the same shape: **Goal** (why this exists), **Overview**
(the modules involved and each one's job), **TL;DR** (one paragraph, no code
diving required), then a detailed, code-grounded walkthrough.

| Pipeline | Source | Covers | Doc |
|---|---|---|---|
| Tennis-Data UK: Fetch | Tennis-Data.co.uk | Download a season, sanity-check it, write the raw checkpoint | [tennis-data-uk-fetch.md](tennis-data-uk-fetch.md) |
| Tennis-Data UK: Clean | Tennis-Data.co.uk | Known-fixes, structural validation, canonical-schema rename, quality report | [tennis-data-uk-clean.md](tennis-data-uk-clean.md) |
| Tennis-Data UK: Tournament Table | Tennis-Data.co.uk | Aggregate clean matches into one row per tournament (champion, dates, consistency check) | [tennis-data-uk-tournaments.md](tennis-data-uk-tournaments.md) |
| Sackmann Archive: Data Access | Sackmann archive (GitHub mirror) | Live download + dtype coercion + `canonical_match_key`; no local checkpoint yet | [sackmann-fetch.md](sackmann-fetch.md) |
| WTA Tournaments API: Fetch | api.wtatennis.com | Paginated download (100/page server cap), flatten, write the raw checkpoint | [wta-api-fetch.md](wta-api-fetch.md) |
| WTA Tournaments API: Tournament Table | api.wtatennis.com | Clean/type into the authoritative `official_tournament_id` source for tournament matching | [wta-api-tournaments.md](wta-api-tournaments.md) |
| Cross-Source Tournament Matching | UK + Sackmann + WTA API | Fuzzy-match tournaments across all 3 sources into one permanent `official_tournament_id`; crosswalk + source-links persistence | [tournament-matching.md](tournament-matching.md) |
| Cross-Source Match Linking | UK + Sackmann | Link individual matches (odds ↔ stats) via manual overrides + rank-pair + name-pair passes; depends on tournament matching | [match-linking.md](match-linking.md) |

This supersedes [docs/scripts/tournament_linker.md](../scripts/tournament_linker.md)
(same pipeline, written before the WTA-API backfill and `manual_matches`
override table existed) — that doc is kept for now but should be considered
stale in its favor.

Match-*level* cross-source linking — the separate pipeline
(`mapper/matches/uk_sackmann/`, `scripts/mapper/link_matches_uk_sackmann.py`)
that links individual matches using this tournament mapping's output — is
not yet documented here.

For where each pipeline fits relative to `datasources`/`handler`/`workflows`/
`loader` as a whole, see the [architecture overview](../architecture/README.md).
