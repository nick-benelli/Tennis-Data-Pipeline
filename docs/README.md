# Documentation

This is the documentation for `tennis_data_pipeline`. Start here, then
follow a link below depending on what you're looking for.

| Folder | What's in it |
|---|---|
| [`architecture/`](architecture/README.md) | System-level architecture: components (`config`/`datasources`/`handler`/`workflows`/`loader`), how data flows between them, configuration, and design decisions. |
| [`pipelines/`](pipelines/README.md) | Process docs for each data pipeline — fetch, clean, tournament-table building, cross-source tournament matching, match linking. Each doc studies the actual code and answers "what does this do, in what order, and why." |
| [`data-sources/`](data-sources/tennis-data-uk/README.md) | Per-source reference material: schema/data dictionary, module-level data flow, and design-rationale plan docs. Currently covers Tennis-Data.co.uk. |
| [`scripts/`](scripts/README.md) | CLI reference for every script under `scripts/`: parameters and example invocations. |
| [`-My-Notes/`](-My-Notes/My-Notes.md) | Personal exploration notes — not maintained documentation. Includes the original prototype script the [match-linking pipeline](pipelines/match-linking.md) was adapted from. |
| [`-scratch/`](-scratch/) | Temporary/scratch reference files kept for convenience (raw HTML dumps, link lists). Not documentation — safe to ignore. |

## Where to start

- **New to the repo?** [architecture/README.md](architecture/README.md) for
  the system overview, then [pipelines/README.md](pipelines/README.md) for
  how each data source actually moves through the system.
- **Running a script?** Go straight to [scripts/README.md](scripts/README.md).
- **Debugging a specific source's data?** Find the relevant doc in
  [pipelines/README.md](pipelines/README.md), then check
  [data-sources/](data-sources/tennis-data-uk/README.md) for the schema.
