"""WTA tournaments API data source."""

from .client import WtaApiClient, WtaApiDownloadError, WtaApiError, flatten_tournament

__all__ = [
    "WtaApiClient",
    "WtaApiDownloadError",
    "WtaApiError",
    "flatten_tournament",
]
