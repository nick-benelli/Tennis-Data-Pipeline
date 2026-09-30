"""Tennis-Data-Pipeline: fetch, clean, and load tennis match data from multiple sources."""

from . import (
    loader,
    workflows,
)


def main() -> None:
    """Entry point for the `tennis-data-pipeline` console script."""
    print("Hello from tennis-data-pipeline!")


__all__ = [
    "main",
    "workflows",
    "loader",
]
