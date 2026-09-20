"""Download all available data files from Tennis Abstract's tennisismylife API."""

from pathlib import Path

from tennis_data_pipeline.datasources.tennis_is_my_life.client import TennisMyLifeClient

OUTPUT_DIR = Path("data/raw/tennis_my_life")


def main() -> None:
    """Download every file listed by the TennisMyLife API into OUTPUT_DIR."""
    client = TennisMyLifeClient()

    for file in client.list_files():
        output_path = OUTPUT_DIR / file["name"]

        print(f"Downloading {file['name']}...")

        client.download_file(
            url=file["url"],
            output_path=output_path,
        )


if __name__ == "__main__":
    main()
