"""Client for the Sackmann tennis archive."""

from __future__ import annotations

from enum import StrEnum
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ...config import settings
from .schema import (
    ATP_MATCHES_DOUBLES_FILE_TEMPLATE,
    ATP_MATCHES_FUTURES_FILE_TEMPLATE,
    ATP_MATCHES_QUAL_CHALL_FILE_TEMPLATE,
    MATCH_FILE_TEMPLATE,
    PLAYER_FILE,
    RANKINGS_CURRENT_FILE,
    WTA_MATCHES_QUAL_ITF_FILE_TEMPLATE,
)


class Tour(StrEnum):
    """Supported professional tennis tours."""

    ATP = "atp"
    WTA = "wta"


class SackmannError(Exception):
    """Base exception for Sackmann archive errors."""


class SackmannDownloadError(SackmannError):
    """Raised when a Sackmann archive file cannot be downloaded."""


class SackmannClient:
    """Client for the Aneeshers Sackmann archive mirror."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
    ) -> None:
        """Initialize the client with a request timeout and retry count.

        Args:
            base_url: Override for the archive's raw-content base URL. Defaults
                to the configured value (see `sackmann.base_url` in config.yaml).
            timeout: Request timeout in seconds.
            retries: Total retry attempts for transient failures.
            backoff_factor: Exponential backoff factor applied between retries.

        """
        sackmann_settings = settings.sackmann

        self.base_url = base_url if base_url is not None else sackmann_settings.base_url
        self.timeout = timeout if timeout is not None else sackmann_settings.request_timeout_seconds

        retries = retries if retries is not None else sackmann_settings.retry_total
        backoff_factor = (
            backoff_factor if backoff_factor is not None else sackmann_settings.retry_backoff_factor
        )

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )

        adapter = HTTPAdapter(max_retries=retry)

        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.headers.update(
            {
                "User-Agent": "tennis-data-pipeline/0.1",
            }
        )

    def build_url(
        self,
        tour: Tour | str,
        filename: str,
    ) -> str:
        """Build a raw GitHub URL."""
        tour = Tour(tour.lower())

        return f"{self.base_url}/{tour.value}/{filename}"

    def load_csv(
        self,
        tour: Tour | str,
        filename: str,
    ) -> pd.DataFrame:
        """Download a CSV from the archive."""
        url = self.build_url(
            tour=tour,
            filename=filename,
        )

        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
            )
            response.raise_for_status()

        except requests.RequestException as error:
            raise SackmannDownloadError(f"Failed to download {url}") from error

        # index_col=False: some archive files (e.g. atp_matches_doubles_*.csv)
        # have trailing blank fields on every data row beyond the declared
        # header. Without this, pandas' default "more data columns than header
        # columns" heuristic treats the extra fields as an implicit leading
        # index, silently shifting every named column's values left.
        return pd.read_csv(
            StringIO(response.text),
            index_col=False,
        )

    def load_matches(
        self,
        year: int,
        tour: Tour | str,
    ) -> pd.DataFrame:
        """Load tour-level singles matches for one year."""
        tour = Tour(tour.lower())

        filename = MATCH_FILE_TEMPLATE.format(tour=tour.value, year=year)

        return self.load_csv(
            tour=tour,
            filename=filename,
        )

    def load_atp_qual_chall_matches(
        self,
        year: int,
    ) -> pd.DataFrame:
        """Load one season of ATP qualifying + Challenger singles matches."""
        filename = ATP_MATCHES_QUAL_CHALL_FILE_TEMPLATE.format(year=year)

        return self.load_csv(
            tour=Tour.ATP,
            filename=filename,
        )

    def load_atp_futures_matches(
        self,
        year: int,
    ) -> pd.DataFrame:
        """Load one season of ATP Futures/ITF World Tennis Tour singles matches."""
        filename = ATP_MATCHES_FUTURES_FILE_TEMPLATE.format(year=year)

        return self.load_csv(
            tour=Tour.ATP,
            filename=filename,
        )

    def load_atp_doubles_matches(
        self,
        year: int,
    ) -> pd.DataFrame:
        """Load one season of ATP doubles matches (archive only covers 2000-2020)."""
        filename = ATP_MATCHES_DOUBLES_FILE_TEMPLATE.format(year=year)

        return self.load_csv(
            tour=Tour.ATP,
            filename=filename,
        )

    def load_wta_qual_itf_matches(
        self,
        year: int,
    ) -> pd.DataFrame:
        """Load one season of WTA qualifying + ITF singles matches."""
        filename = WTA_MATCHES_QUAL_ITF_FILE_TEMPLATE.format(year=year)

        return self.load_csv(
            tour=Tour.WTA,
            filename=filename,
        )

    def load_players(
        self,
        tour: Tour | str,
    ) -> pd.DataFrame:
        """Load the player biography table for a tour."""
        tour = Tour(tour.lower())

        return self.load_csv(
            tour=tour,
            filename=PLAYER_FILE[tour.value],
        )

    def load_rankings_current(
        self,
        tour: Tour | str,
    ) -> pd.DataFrame:
        """Load the most recent rankings snapshot for a tour."""
        tour = Tour(tour.lower())

        return self.load_csv(
            tour=tour,
            filename=RANKINGS_CURRENT_FILE[tour.value],
        )
