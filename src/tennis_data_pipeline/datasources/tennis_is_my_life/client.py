"""Client for the Tennis Is My Life stats site."""

from io import BytesIO
from pathlib import Path

import pandas as pd
import requests


class TennisMyLifeClient:
    """Client for downloading data files from stats.tennismylife.org."""

    BASE_URL = "https://stats.tennismylife.org"
    FILES_URL = f"{BASE_URL}/api/data-files"

    def __init__(self, timeout: int = 30):
        """Initialize the client with a request timeout."""
        self.timeout = timeout
        self.session = requests.Session()

    def list_files(self) -> list[dict]:
        """List available data files from the site's API."""
        response = self.session.get(
            self.FILES_URL,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return response.json()["files"]

    def read_csv(self, url: str) -> pd.DataFrame:
        """Download and parse a CSV file from `url` into a DataFrame."""
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()

        return pd.read_csv(BytesIO(response.content))

    def download_file(
        self,
        url: str,
        output_path: Path,
    ) -> Path:
        """Download the file at `url` and write it to `output_path`."""
        response = self.session.get(
            url,
            timeout=self.timeout,
        )
        response.raise_for_status()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output_path.write_bytes(response.content)

        return output_path
