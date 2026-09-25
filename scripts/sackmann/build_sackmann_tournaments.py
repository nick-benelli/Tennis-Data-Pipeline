"""Build/update the Sackmann tournament-summary table.

Thin CLI wrapper around `tennis_data_pipeline.workflows.sackmann.build_sackmann_tournaments`
- all the actual grouping/summarizing logic lives in the package
  (`handler/sackmann/tournaments.py`) so it's reusable outside this script too.

Unlike the Tennis-Data UK pipeline, there's no local raw/clean checkpoint for
Sackmann data yet - each run downloads the requested seasons live from the
archive mirror, so it needs network access.

Writes one row per tournament to
data/clean/sackmann/<tour>/tournaments/sackmann_<tour>_tournaments.csv, plus a
companion sackmann_<tour>_tournament_inconsistencies.csv for any tournament
whose attributes (name/level/surface/best_of/draw_size) aren't consistent
across its matches.

Usage:
    python scripts/sackmann/build_sackmann_tournaments.py --tour atp 2000-2024
    python scripts/sackmann/build_sackmann_tournaments.py --tour wta 2019 2015 2013
    python scripts/sackmann/build_sackmann_tournaments.py --tour atp 2024
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.workflows.sackmann import build_sackmann_tournaments

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


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
        help="One or more years and/or ranges, e.g. 2024 2019 2000-2015",
    )
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=None,
        help="Override the Sackmann tournament-table output directory (default: config-driven)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build/update the Sackmann tournament-summary table for the specified tour and years.

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
        "Building %s Sackmann tournaments, %d year(s): %s",
        args.tour.upper(),
        len(years),
        ", ".join(map(str, years)),
    )

    table_path, tournament_count, inconsistency_count = build_sackmann_tournaments(
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
