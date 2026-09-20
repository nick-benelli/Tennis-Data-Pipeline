"""Archived, pre-client version of the tennisismylife data-file downloader."""

from pathlib import Path

import requests

API_URL = "https://stats.tennismylife.org/api/data-files"
OUTPUT_DIR = Path("data/raw/tennis_my_life")


def download_all_files() -> None:
    """Download every file listed by the data-files API into OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    response = requests.get(API_URL, timeout=30)
    response.raise_for_status()

    files = response.json()["files"]

    for file in files:
        url = file["url"]
        name = file["name"]

        output_path: Path = OUTPUT_DIR / name
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Downloading {name}...")

        file_response = requests.get(url, timeout=60)
        file_response.raise_for_status()

        output_path.write_bytes(file_response.content)


if __name__ == "__main__":
    download_all_files()
