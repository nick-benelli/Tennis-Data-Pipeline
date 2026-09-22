# Scripts

[← Architecture overview](../architecture/README.md)

`scripts/` holds thin CLI entry points around `workflows` (see
[architecture: Repository Structure](../architecture/README.md#repository-structure)).
Most scripts are self-explanatory from their own docstring/`--help` output;
this directory documents the ones whose behavior is worth explaining in more
depth than that.

| Script | Purpose | Doc |
|---|---|---|
| `scripts/mapper/build_tournament_mapping.py` | Cross-source (Tennis-Data UK ↔ Sackmann ↔ permanent ATP id) tournament mapping | [tournament_linker.md](tournament_linker.md) |

For everything else (`scripts/uk/*.py`, `scripts/sackmann/*.py`,
`scripts/timl/*.py`), read the script's module docstring or run it with
`--help`.
