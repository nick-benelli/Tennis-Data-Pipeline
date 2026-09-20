"""Client for the Sackmann tennis archive."""

from __future__ import annotations

from enum import StrEnum
from io import StringIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


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

    BASE_URL = (
        "https://raw.githubusercontent.com/Aneeshers/tennis-sackmann-archive/main"
    )

    def __init__(
        self,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        """Initialize the client with a request timeout and retry count."""
        self.timeout = timeout

        retry = Retry(
            total=retries,
            connect=retries,
            read=retries,
            status=retries,
            backoff_factor=1.0,
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

        return f"{self.BASE_URL}/{tour.value}/{filename}"

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

        return pd.read_csv(
            StringIO(response.text),
        )

    def load_matches(
        self,
        year: int,
        tour: Tour | str,
    ) -> pd.DataFrame:
        """Load tour-level singles matches for one year."""
        tour = Tour(tour.lower())

        filename = f"{tour.value}_matches_{year}.csv"

        return self.load_csv(
            tour=tour,
            filename=filename,
        )
