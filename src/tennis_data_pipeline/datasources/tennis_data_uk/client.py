"""Client for downloading match data from Tennis-Data.co.uk."""

from __future__ import annotations

from enum import StrEnum
from io import BytesIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ...config import settings


class Tour(StrEnum):
    """Supported professional tennis tours."""

    ATP = "atp"
    WTA = "wta"


class TennisDataUKError(Exception):
    """Base exception for Tennis-Data UK errors."""


class TennisDataUKDownloadError(TennisDataUKError):
    """Raised when a Tennis-Data UK file cannot be downloaded."""


class TennisDataUKClient:
    """Client for downloading ATP and WTA data from Tennis-Data.co.uk."""

    BASE_HOST = "www.tennis-data.co.uk"

    # Tennis-Data UK served .xls before this season and .xlsx from this season onward.
    _LEGACY_EXTENSION_CUTOFF_YEAR = 2012

    def __init__(
        self,
        timeout: float | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
        allow_http_fallback: bool = True,
    ) -> None:
        """
        Initialize the TennisDataUKClient.

        Args:
            timeout (float | None): The request timeout in seconds.
            retries (int | None): The total number of retry attempts.
            backoff_factor (float | None): The backoff factor for retries.
            allow_http_fallback (bool): Whether to allow HTTP fallback if HTTPS fails.
        """
        tennis_data_uk_settings = settings.tennis_data_uk

        self.timeout = (
            timeout
            if timeout is not None
            else tennis_data_uk_settings.request_timeout_seconds
        )

        retries = (
            retries
            if retries is not None
            else tennis_data_uk_settings.retry_total
        )

        backoff_factor = (
            backoff_factor
            if backoff_factor is not None
            else tennis_data_uk_settings.retry_backoff_factor
        )

        self.allow_http_fallback = allow_http_fallback

        self.session = self._create_session(
            retries=retries,
            backoff_factor=backoff_factor,
        )

    @staticmethod
    def _create_session(
        retries: int,
        backoff_factor: float,
    ) -> requests.Session:
        """Create and configure a requests session with retry strategy."""
        retry_strategy = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )

        adapter = HTTPAdapter(
            max_retries=retry_strategy,
        )

        session = requests.Session()

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({"User-Agent": "tennis-data-pipeline/0.1"})

        return session

    @staticmethod
    def _year_directory(
        year: int,
        tour: Tour,
    ) -> str:
        """
        Get the directory name for a given year and tour.
        ATP: "http://tennis-data.co.uk/{year}/{year}.xlsx",
        WTA: "http://tennis-data.co.uk/{year}w/{year}.xlsx",

        Args:
            year (int): The year of the data.
            tour (Tour): The tour (ATP or WTA).

        

        Returns:
            str: The directory name corresponding to the year and tour.
        """
        if tour == Tour.ATP:
            return str(year)

        return f"{year}w"

    @classmethod
    def _extension_order(cls, year: int) -> tuple[str, str]:
        """Return (preferred, fallback) file extensions to try for a given season."""
        if year <= cls._LEGACY_EXTENSION_CUTOFF_YEAR:
            return "xls", "xlsx"

        return "xlsx", "xls"

    def build_url(
        self,
        year: int,
        tour: Tour | str,
        *,
        scheme: str = "https",
        extension: str = "xlsx",
    ) -> str:
        """
        Build the URL for downloading a specific year's data for the given tour.

        Args:
            year (int): The year of the data to download.
            tour (Tour | str): The tour (ATP or WTA) for which to download data.
            scheme (str, optional): The URL scheme to use (default is "https").
            extension (str, optional): The file extension to use (default is "xlsx").

        Returns:
            str: The constructed URL.
        """
        tour = Tour(tour.lower())

        directory = self._year_directory(
            year,
            tour,
        )

        return (
            f"{scheme}://{self.BASE_HOST}/"
            f"{directory}/{year}.{extension}"
        )

    def _fetch(
        self,
        url: str,
    ) -> bytes:
        response = self.session.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.content

    @staticmethod
    def _is_not_found(error: requests.RequestException) -> bool:
        """Return True for a definitive 404 (retrying via another scheme won't help)."""
        response = getattr(error, "response", None)

        return response is not None and response.status_code == 404

    def _try_urls(
        self,
        urls: list[str],
    ) -> tuple[bytes | None, list[str], bool]:
        """Try each URL in order, returning the first success.

        Returns a tuple of (content, error messages, all attempts were 404).
        """
        errors: list[str] = []
        all_not_found = True

        for url in urls:
            try:
                return self._fetch(url), errors, all_not_found

            except requests.RequestException as error:
                errors.append(f"{url}: {error}")
                all_not_found = all_not_found and self._is_not_found(error)

        return None, errors, all_not_found

    def download_year(
        self,
        year: int,
        tour: Tour | str,
    ) -> bytes:
        tour = Tour(tour.lower())
        extensions = self._extension_order(year)

        https_urls = [
            self.build_url(year, tour, scheme="https", extension=extension)
            for extension in extensions
        ]
        content, https_errors, all_not_found = self._try_urls(https_urls)

        if content is not None:
            return content

        if not self.allow_http_fallback or all_not_found:
            raise TennisDataUKDownloadError(
                f"Failed to download {tour.upper()} {year}:\n"
                + "\n".join(https_errors)
            )

        http_urls = [
            self.build_url(year, tour, scheme="http", extension=extension)
            for extension in extensions
        ]
        content, http_errors, _ = self._try_urls(http_urls)

        if content is not None:
            return content

        raise TennisDataUKDownloadError(
            f"Failed to download {tour.upper()} {year} over HTTPS and HTTP:\n"
            + "\n".join(https_errors + http_errors)
        )

    def load_year(
        self,
        year: int,
        tour: Tour | str,
    ) -> pd.DataFrame:
        contents = self.download_year(
            year=year,
            tour=tour,
        )

        return pd.read_excel(
            BytesIO(contents),
        )
    