"""Client for downloading historical tennis data from Tennis-Data.co.uk."""

from __future__ import annotations

from enum import StrEnum
from io import BytesIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class Tour(StrEnum):
    """Supported professional tennis tours."""

    ATP = "atp"
    WTA = "wta"


class TennisDataUKError(Exception):
    """Base exception for Tennis-Data UK errors."""


class TennisDataUKDownloadError(TennisDataUKError):
    """Raised when a Tennis-Data UK file cannot be downloaded."""


class TennisDataUKClient:
    """Client for downloading ATP and WTA data from Tennis-Data.co.uk.

    Parameters
    ----------
    timeout
        Number of seconds to wait for an HTTP response.
    retries
        Number of times to retry transient HTTP failures.
    allow_http_fallback
        Whether to retry a failed HTTPS request over HTTP.
    """

    BASE_HOST = "www.tennis-data.co.uk"

    def __init__(
        self,
        timeout: float = 30.0,
        retries: int = 3,
        allow_http_fallback: bool = True,
    ) -> None:
        self.timeout = timeout
        self.allow_http_fallback = allow_http_fallback
        self.session = self._create_session(retries)

    @staticmethod
    def _create_session(retries: int) -> requests.Session:
        """Create an HTTP session with retry behavior."""
        retry_strategy = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)

        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    @staticmethod
    def _year_directory(year: int, tour: Tour) -> str:
        """Return the Tennis-Data UK directory for a tour and year."""
        if tour == Tour.ATP:
            return str(year)

        if tour == Tour.WTA:
            return f"{year}w"

        raise ValueError(f"Unsupported tour: {tour}")

    def build_url(
        self,
        year: int,
        tour: Tour | str,
        *,
        scheme: str = "https",
    ) -> str:
        """Build the URL for a Tennis-Data UK season file."""
        tour = Tour(tour.lower())

        directory = self._year_directory(year, tour)

        return f"{scheme}://{self.BASE_HOST}/" f"{directory}/{year}.xlsx"

    def _download_url(self, url: str) -> bytes:
        """Download a file and return its raw contents."""
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return response.content

    def download_year(
        self,
        year: int,
        tour: Tour | str,
    ) -> bytes:
        """Download one season from Tennis-Data UK.

        HTTPS is attempted first. If that fails and HTTP fallback is enabled,
        the same file is requested over HTTP.

        Returns
        -------
        bytes
            Raw Excel file contents.

        Raises
        ------
        TennisDataUKDownloadError
            If all download attempts fail.
        """
        tour = Tour(tour.lower())

        https_url = self.build_url(
            year,
            tour,
            scheme="https",
        )

        try:
            return self._download_url(https_url)

        except requests.RequestException as https_error:
            if not self.allow_http_fallback:
                raise TennisDataUKDownloadError(
                    f"Failed to download {tour.upper()} {year} " f"from {https_url}"
                ) from https_error

        http_url = self.build_url(
            year,
            tour,
            scheme="http",
        )

        try:
            return self._download_url(http_url)

        except requests.RequestException as http_error:
            raise TennisDataUKDownloadError(
                f"Failed to download {tour.upper()} {year} " "over both HTTPS and HTTP."
            ) from http_error

    def load_year(
        self,
        year: int,
        tour: Tour | str,
    ) -> pd.DataFrame:
        """Download a season and return it as a pandas DataFrame."""
        contents = self.download_year(
            year=year,
            tour=tour,
        )

        return pd.read_excel(BytesIO(contents))
