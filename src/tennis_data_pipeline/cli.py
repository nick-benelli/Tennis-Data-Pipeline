"""Shared CLI argument-parsing helpers for the year-based scripts under `scripts/`.

Every `scripts/**/*.py` entry point that takes one or more years on the
command line (`2022`, `2010-2015`, or a mix) uses the same expansion logic -
this module is the single implementation, imported by each script instead of
being copy-pasted per script.
"""

from __future__ import annotations

import argparse


def _parse_year_token(token: str) -> list[int]:
    """Expand a single CLI token: "2022" -> [2022], "2010-2015" -> [2010..2015]."""
    token = token.strip()

    if "-" in token:
        start_str, _, end_str = token.partition("-")
        try:
            start, end = int(start_str), int(end_str)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"Invalid year range '{token}'") from exc
        if start > end:
            raise argparse.ArgumentTypeError(f"Invalid year range '{token}': start > end")
        return list(range(start, end + 1))

    try:
        return [int(token)]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid year '{token}'") from exc


def parse_years(tokens: list[str]) -> list[int]:
    """Expand and de-duplicate a mix of single years and ranges, e.g. ["2022", "2010-2015"]."""
    years: set[int] = set()
    for token in tokens:
        years.update(_parse_year_token(token))
    return sorted(years)


__all__ = ["parse_years"]
