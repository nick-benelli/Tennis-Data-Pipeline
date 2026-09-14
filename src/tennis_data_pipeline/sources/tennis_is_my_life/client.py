from pathlib import Path

import requests


BASE_URL = "https://stats.tennismylife.org"
FILES_URL = f"{BASE_URL}/api/data-files"


class TennisMyLifeClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()

    def list_files(self) -> list[dict]:
        response = self.session.get(FILES_URL, timeout=self.timeout)
        response.raise_for_status()

        data = response.json()
        return data["files"]

    def download_file(
        self,
        url: str,
        output_path: Path,
    ) -> Path:
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        return output_path