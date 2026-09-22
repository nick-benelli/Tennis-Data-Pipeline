"""Client for the WTA tournaments API (api.wtatennis.com)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ...config import settings
from .cleaner import flatten_tournament

# The API's TLS certificate fails verification (see WtaApiConfig.verify_ssl), so
# suppress the resulting per-request InsecureRequestWarning noise.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WtaApiError(Exception):
    """Base exception for WTA tournaments API errors."""


class WtaApiDownloadError(WtaApiError):
    """Raised when the WTA tournaments API can't be reached or returns an error."""


class WtaApiClient:
    """Client for the public WTA tournaments API."""

    TOURNAMENTS_PATH = "/tennis/tournaments/"

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        backoff_factor: float | None = None,
        page_size: int | None = None,
        verify_ssl: bool | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            base_url: Override for the API's base URL. Defaults to the
                configured value (see `wta_api.base_url` in config.yaml).
            timeout: Request timeout in seconds.
            retries: Total retry attempts for transient failures.
            backoff_factor: Exponential backoff factor applied between retries.
            page_size: Default page size used by `get_tournaments()`.
            verify_ssl: Whether to verify the server's TLS certificate.

        """
        wta_api_settings = settings.wta_api

        self.base_url = base_url if base_url is not None else wta_api_settings.base_url
        self.timeout = timeout if timeout is not None else wta_api_settings.request_timeout_seconds
        self.page_size = page_size if page_size is not None else wta_api_settings.page_size
        self.verify_ssl = verify_ssl if verify_ssl is not None else wta_api_settings.verify_ssl

        retries = retries if retries is not None else wta_api_settings.retry_total
        backoff_factor = (
            backoff_factor if backoff_factor is not None else wta_api_settings.retry_backoff_factor
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
        self.session.headers.update({"User-Agent": "tennis-data-pipeline/0.1"})

    def get_tournaments_page(
        self,
        year: int,
        *,
        page: int = 0,
        page_size: int | None = None,
        exclude_levels: str | Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """Fetch one page of raw tournament entries for `year`.

        `exclude_levels` filters out tournament levels server-side (e.g. `"ITF"`
        or `["ITF", "WTA 125"]`), matching the API's `excludeLevels` query param.

        Returns the raw JSON response (`{"pageInfo": {...}, "content": [...]}`).
        """
        params: dict[str, Any] = {
            "page": page,
            "pageSize": page_size if page_size is not None else self.page_size,
            "from": f"{year}-01-01",
            "to": f"{year}-12-31",
        }

        if exclude_levels:
            levels = [exclude_levels] if isinstance(exclude_levels, str) else list(exclude_levels)
            params["excludeLevels"] = ",".join(levels)

        try:
            response = self.session.get(
                f"{self.base_url}{self.TOURNAMENTS_PATH}",
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise WtaApiDownloadError(f"Failed to fetch WTA tournaments for {year}: {error}") from error

        result: dict[str, Any] = response.json()
        return result

    def iter_tournament_entries(
        self,
        year: int,
        *,
        exclude_levels: str | Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch every raw tournament entry for `year`, paging until exhausted."""
        entries: list[dict[str, Any]] = []
        page = 0

        while True:
            payload = self.get_tournaments_page(year, page=page, exclude_levels=exclude_levels)
            content = payload.get("content") or []

            if not content:
                break

            entries.extend(content)
            page += 1

        return entries

    def get_tournaments(
        self,
        year: int,
        *,
        exclude_levels: str | Iterable[str] | None = None,
    ) -> pd.DataFrame:
        """Fetch every tournament for `year` as a flat DataFrame (one row each)."""
        entries = self.iter_tournament_entries(year, exclude_levels=exclude_levels)

        return pd.DataFrame(flatten_tournament(entry) for entry in entries)
