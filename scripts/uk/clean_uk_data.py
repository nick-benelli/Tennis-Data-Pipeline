"""Clean Tennis-Data UK season CSVs (raw -> validated -> clean) from the CLI.

Thin CLI wrapper around `tennis_data_pipeline.workflows.tennis_data_uk.clean_years`
- all the actual known-fixes/validation/cleaning logic lives in the package
  (`handler/uk/cleaner/atp.py`/`wta.py`) so it's reusable outside this script too.

Usage:
    python scripts/uk/clean_uk_data.py --tour atp 2022
    python scripts/uk/clean_uk_data.py --tour wta 2019 2015 2013
    python scripts/uk/clean_uk_data.py --tour atp 2010-2023
    python scripts/uk/clean_uk_data.py --tour wta 2007-2015 2020-2023 --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.workflows.tennis_data_uk import clean_years, log_clean_summary

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--tour",
        choices=_TOURS,
        required=True,
        help="Tour to clean",
    )
    parser.add_argument(
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2022 2019 2010-2015",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Override the Stage-2 raw checkpoint directory (default: config-driven)",
    )
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=None,
        help="Override the Stage-4 clean checkpoint directory (default: config-driven)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first year that fails instead of processing the rest",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Clean UK tennis data for the specified tour and years.
    Args:
        argv: Optional list of command-line arguments to parse. If None, defaults to sys.argv.

    Returns:
        Exit code: 0 if all years were processed successfully, 1 if any year failed, 2 if there was an argument parsing error.
    """
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        years = parse_years(args.years)
    except argparse.ArgumentTypeError as exc:
        logger.error("Invalid year argument: %s", exc)
        return 2

    logger.info(
        "Processing %s, %d year(s): %s", args.tour.upper(), len(years), ", ".join(map(str, years)),
    )

    results = clean_years(
        args.tour,
        years,
        raw_dir=args.raw_dir,
        clean_dir=args.clean_dir,
        fail_fast=args.fail_fast,
    )
    log_clean_summary(args.tour, results)

    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
