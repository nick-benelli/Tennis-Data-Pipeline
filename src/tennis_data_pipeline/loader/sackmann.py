"""Load Sackmann archive data from a local repo clone instead of the network mirror.

`LocalSackmannClient` is a drop-in `SackmannClient` that overrides only
`load_csv` to read from disk. Every higher-level method - `load_matches`,
`load_atp_qual_chall_matches`, `load_wta_qual_itf_matches`, etc. - is inherited
unchanged, so `datasources.sackmann.atp`/`wta` apply the exact same cleaning
and metadata pipeline (`clean_matches`/`clean_doubles_matches`, `source_year`/
`tour`/`match_type`/`match_level` tagging) regardless of where the raw CSV
came from.

The functions below just call `atp`/`wta` with a `LocalSackmannClient`, so any
loader not wrapped here (e.g. `atp.load_year(2024, client=LocalSackmannClient())`)
works exactly the same way.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from ..config import settings
from ..datasources.sackmann import atp, wta
from ..datasources.sackmann.client import SackmannClient, SackmannDownloadError, SackmannError, Tour


def _resolve_local_dir(local_dir: Path | str | None) -> Path:
    """Resolve `local_dir`, falling back to `settings.sackmann.local_dir`.

    Relative paths (either the argument or the config default) resolve
    against `settings.paths.project_dir`, matching the `paths.*_dir` convention.
    """
    if local_dir is None:
        local_dir = settings.sackmann.local_dir
        if local_dir is None:
            raise SackmannError(
                "No local Sackmann archive directory configured. Pass `local_dir=` "
                "or set `sackmann.local_dir` in config.yaml."
            )

    path = Path(local_dir).expanduser()
    return path if path.is_absolute() else settings.paths.project_dir / path


class LocalSackmannClient(SackmannClient):
    """`SackmannClient` that reads CSVs from a local archive clone instead of GitHub."""

    def __init__(self, local_dir: Path | str | None = None) -> None:  # pylint: disable=super-init-not-called
        # Deliberately skips SackmannClient.__init__: no HTTP session is needed for local reads.
        self.local_dir = _resolve_local_dir(local_dir)

    def load_csv(self, tour: Tour | str, filename: str) -> pd.DataFrame:
        """Read `<local_dir>/<tour>/<filename>` off disk instead of downloading it."""
        tour = Tour(tour.lower())
        path = self.local_dir / tour.value / filename

        if not path.is_file():
            raise SackmannDownloadError(f"Local Sackmann archive file not found: {path}")

        # index_col=False: see SackmannClient.load_csv - some archive files have
        # trailing blank fields that would otherwise be misread as an index.
        return pd.read_csv(path, index_col=False)


# -------- ATP --------


def load_atp_year(year: int, *, local_dir: Path | str | None = None, clean: bool = True) -> pd.DataFrame:
    """Load one ATP season of tour-level singles matches from a local archive clone."""
    return atp.load_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple ATP seasons of tour-level singles matches from a local archive clone."""
    return atp.load_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive ATP year range of tour-level singles matches from a local archive clone."""
    return atp.load_range(start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_qual_chall_year(
    year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load one ATP season of qualifying + Challenger singles matches from a local archive clone."""
    return atp.load_qual_chall_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_qual_chall_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple ATP seasons of qualifying + Challenger matches from a local archive clone."""
    return atp.load_qual_chall_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_qual_chall_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive ATP year range of qualifying + Challenger matches from a local clone."""
    return atp.load_qual_chall_range(
        start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean
    )


def load_atp_futures_year(
    year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load one ATP season of Futures/ITF World Tennis Tour matches from a local archive clone."""
    return atp.load_futures_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_futures_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple ATP seasons of Futures/ITF World Tennis Tour matches from a local clone."""
    return atp.load_futures_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_futures_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive ATP year range of Futures/ITF matches from a local archive clone."""
    return atp.load_futures_range(
        start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean
    )


def load_atp_doubles_year(
    year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load one ATP season of doubles matches from a local clone (archive covers 2000-2020)."""
    return atp.load_doubles_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_doubles_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple ATP seasons of doubles matches from a local archive clone."""
    return atp.load_doubles_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_atp_doubles_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive ATP year range of doubles matches from a local archive clone."""
    return atp.load_doubles_range(
        start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean
    )


# -------- WTA --------


def load_wta_year(year: int, *, local_dir: Path | str | None = None, clean: bool = True) -> pd.DataFrame:
    """Load one WTA season of tour-level singles matches from a local archive clone."""
    return wta.load_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_wta_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple WTA seasons of tour-level singles matches from a local archive clone."""
    return wta.load_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_wta_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive WTA year range of tour-level singles matches from a local archive clone."""
    return wta.load_range(start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean)


def load_wta_qual_itf_year(
    year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load one WTA season of qualifying + ITF singles matches from a local archive clone."""
    return wta.load_qual_itf_year(year, client=LocalSackmannClient(local_dir), clean=clean)


def load_wta_qual_itf_years(
    years: Iterable[int], *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load multiple WTA seasons of qualifying + ITF singles matches from a local archive clone."""
    return wta.load_qual_itf_years(years, client=LocalSackmannClient(local_dir), clean=clean)


def load_wta_qual_itf_range(
    start_year: int, end_year: int, *, local_dir: Path | str | None = None, clean: bool = True
) -> pd.DataFrame:
    """Load an inclusive WTA year range of qualifying + ITF matches from a local archive clone."""
    return wta.load_qual_itf_range(
        start_year, end_year, client=LocalSackmannClient(local_dir), clean=clean
    )


__all__ = [
    "LocalSackmannClient",
    "load_atp_year",
    "load_atp_years",
    "load_atp_range",
    "load_atp_qual_chall_year",
    "load_atp_qual_chall_years",
    "load_atp_qual_chall_range",
    "load_atp_futures_year",
    "load_atp_futures_years",
    "load_atp_futures_range",
    "load_atp_doubles_year",
    "load_atp_doubles_years",
    "load_atp_doubles_range",
    "load_wta_year",
    "load_wta_years",
    "load_wta_range",
    "load_wta_qual_itf_year",
    "load_wta_qual_itf_years",
    "load_wta_qual_itf_range",
]
