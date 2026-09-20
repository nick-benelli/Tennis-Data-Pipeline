"""Build/update the Tennis-Data UK tournament-summary table from Stage-4 clean checkpoints.

Thin CLI wrapper around `tennis_data_pipeline.workflows.uk.build_uk_tournaments`
- all the actual grouping/summarizing logic lives in the package
  (`handler/uk/cleaner/tournaments.py`) so it's reusable outside this script too.

Requires the requested years to already be cleaned (see `scripts/uk/clean_uk_data.py`);
years without a clean checkpoint are skipped with a warning.

Writes one row per tournament to data/clean/uk/<tour>/tournaments/uk_<tour>_tournaments.csv,
plus a companion uk_<tour>_tournament_inconsistencies.csv for any tournament whose
attributes (name/series/surface/best_of/court) aren't consistent across its matches.

Usage:
    python scripts/uk/build_uk_tournaments.py --tour atp 2022
    python scripts/uk/build_uk_tournaments.py --tour wta 2019 2015 2013
    python scripts/uk/build_uk_tournaments.py --tour atp 2010-2023
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.workflows.uk import build_uk_tournaments

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
        help="Tour to build tournaments for",
    )
    parser.add_argument(
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2022 2019 2010-2015",
    )
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=None,
        help="Override the Stage-4 clean checkpoint directory (default: config-driven)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build/update the tournament-summary table for the specified tour and years.

    Args:
        argv: Optional list of command-line arguments to parse. If None, defaults to sys.argv.

    Returns:
        Exit code: 0 on success, 2 if there was an argument parsing error.

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
        "Building %s tournaments, %d year(s): %s",
        args.tour.upper(),
        len(years),
        ", ".join(map(str, years)),
    )

    table_path, tournament_count, inconsistency_count = build_uk_tournaments(
        args.tour, years, clean_dir=args.clean_dir
    )

    logger.info(
        "%s: %d tournament(s) in %s (%d inconsistent)",
        args.tour.upper(),
        tournament_count,
        table_path,
        inconsistency_count,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
