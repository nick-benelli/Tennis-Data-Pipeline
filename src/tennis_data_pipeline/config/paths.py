"""Define paths for the package and project directories."""

from pathlib import Path

PACKAGE_DIR: Path = Path(__file__).resolve().parents[1]
PROJECT_DIR: Path = PACKAGE_DIR.parents[1]
