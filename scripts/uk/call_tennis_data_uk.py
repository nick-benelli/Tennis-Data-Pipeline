"""Download Tennis-Data.co.uk season(s) and write them to the Stage-2 raw checkpoint.

Where/how snapshots are named comes entirely from config (configs/config.yaml's
`paths.raw_dir` + `tennis_data_uk.raw_dir_name`/`raw_filename_template`) - this
script only decides *which* tour/season(s) to fetch, and whether to persist
the result at all.

Usage:
    # Single season.
    python scripts/uk/call_tennis_data_uk.py --tour atp --year 2024

    # Range of seasons (--end-year defaults to --year or the current year).
    python scripts/uk/call_tennis_data_uk.py --tour wta --start-year 2020 --end-year 2024

    # No year given: defaults to the current season.
    python scripts/uk/call_tennis_data_uk.py --tour atp

    # Dry run: download and report row counts, but don't write the checkpoint.
    python scripts/uk/call_tennis_data_uk.py --tour atp --year 2024 --no-write
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from tennis_data_pipeline.datasources.tennis_data_uk.client import TennisDataUKClient
from tennis_data_pipeline.workflows.uk import fetch_and_checkpoint_year

_DEFAULT_START_YEAR = {"atp": 2000, "wta": 2007}


def _resolve_years(
    tour: str,
    *,
    year: int | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    """Turn --year/--start-year/--end-year into the sorted list of seasons to fetch."""
    current_year = dt.datetime.now().astimezone().year
    years: set[int] = set()

    if start_year is not None or end_year is not None:
        range_start = (
            start_year if start_year is not None else _DEFAULT_START_YEAR[tour]
        )
        range_end = end_year if end_year is not None else (year or current_year)
        if range_end < range_start:
            raise ValueError(
                f"--end-year ({range_end}) is before --start-year ({range_start}) - "
                "check for a typo (e.g. a missing digit)."
            )
        years.update(range(range_start, range_end + 1))

    if year is not None:
        years.add(year)

    if not years:
        years.add(current_year)

    return sorted(years)


def fetch_years(tour: str, years: list[int], *, write: bool) -> None:
    """Fetch each season, checkpointing it unless `write` is False (dry run)."""
    client = TennisDataUKClient()

    for year in years:
        if write:
            path = fetch_and_checkpoint_year(tour, year, client=client)
            print(f"[{tour.upper()} {year}] wrote snapshot to {path}")
        else:
            df = client.load_year(year=year, tour=tour)
            print(
                f"[{tour.upper()} {year}] downloaded {len(df):,} rows (not written; --no-write)"
            )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--tour",
        choices=sorted(_DEFAULT_START_YEAR),
        required=True,
        help="Tour to download",
    )
    parser.add_argument("--year", type=int, default=None, help="Single season to fetch")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="First season of a range to fetch (default: 2000 for ATP, 2007 for WTA)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last season of a range to fetch (default: --year, or the current year)",
    )
    parser.add_argument(
        "--write",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write the raw snapshot checkpoint (default: True; use --no-write for a dry run)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args and fetch/checkpoint the resolved season(s)."""
    args = _parse_args(argv)

    try:
        years = _resolve_years(
            args.tour,
            year=args.year,
            start_year=args.start_year,
            end_year=args.end_year,
        )
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    fetch_years(args.tour, years, write=args.write)
    return 0


if __name__ == "__main__":
    sys.exit(main())
