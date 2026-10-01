"""Stage: load Sackmann match-level data enriched with per-set score features.

Unlike `workflows.sackmann.tournaments`, this doesn't persist anything - there
is no clean checkpoint for Sackmann match-level data yet (see
docs/pipelines/sackmann-fetch.md's "Known limitations"). What this module
does provide is the one call that ties fetching (network via
`datasources.sackmann.atp`/`wta`, or a local archive clone via
`loader.sackmann`) together with `handler.sackmann.scores.build_score_features`,
so every consumer gets per-set winner/loser games, tiebreak points, and
`match_status` without having to remember to call `build_score_features`
themselves after loading.

Only covers tour-level singles (the same scope as
`workflows.sackmann.tournaments`) - for qual/challenger, futures, qual+ITF,
or doubles matches, load them via `datasources.sackmann.atp`/`wta` or
`loader.sackmann` directly and call `build_score_features` on the result.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from ...datasources.sackmann import atp, wta
from ...datasources.sackmann.client import Tour
from ...handler.sackmann.scores import build_score_features
from ...loader import sackmann as local_sackmann

_NETWORK_LOADERS = {
    Tour.ATP: atp,
    Tour.WTA: wta,
}
_LOCAL_LOADER_NAMES = {
    Tour.ATP: "load_atp_years",
    Tour.WTA: "load_wta_years",
}


def load_matches(tour: Tour | str, years: Iterable[int], *, chronological: bool = False) -> pd.DataFrame:
    """Download tour-level singles matches for `years` and add per-set score features.

    Network equivalent of `load_local_matches` - downloads live from the
    archive mirror (`datasources.sackmann.atp`/`wta`.load_years) rather than
    a local clone. Pass `chronological=True` to reorder matches to
    chronological order (see `datasources.sackmann.cleaning.sort_chronologically`)
    instead of the raw archive's final-to-first-round order.
    """
    tour = Tour(str(tour).lower())
    df = _NETWORK_LOADERS[tour].load_years(years, chronological=chronological)
    return build_score_features(df)


def load_local_matches(
    tour: Tour | str,
    years: Iterable[int],
    *,
    local_dir: Path | str | None = None,
    chronological: bool = False,
) -> pd.DataFrame:
    """Load tour-level singles matches for `years` from a local archive clone and add score features.

    Local-clone equivalent of `load_matches` - see `loader.sackmann` for how
    `local_dir` is resolved. Pass `chronological=True` to reorder matches to
    chronological order instead of the raw archive's final-to-first-round order.
    """
    tour = Tour(str(tour).lower())
    loader_fn = getattr(local_sackmann, _LOCAL_LOADER_NAMES[tour])
    df = loader_fn(years, local_dir=local_dir, chronological=chronological)
    return build_score_features(df)


__all__ = ["load_local_matches", "load_matches"]
