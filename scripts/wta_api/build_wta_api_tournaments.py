"""Build/update the WTA-tournaments-API tournament-summary table.

Thin CLI wrapper around `tennis_data_pipeline.workflows.wta_api.build_wta_api_tournaments`
- fetches every tournament (all levels, ITF included) from api.wtatennis.com
for the requested seasons, so it needs network access.

Writes one row per tournament to
data/clean/wta_api/tournaments/wta_api_tournaments.csv, keyed on
tour/year/official_tournament_id - `official_tournament_id` comes straight
from the WTA's own permanent tournamentGroup.id (see
handler/wta_api/tournaments.py), making this table the most authoritative
cross-reference for the tournament id mapping system (mapper/tournaments.py).

Usage:
    python scripts/wta_api/build_wta_api_tournaments.py 2026
    python scripts/wta_api/build_wta_api_tournaments.py 2020-2026
    python scripts/wta_api/build_wta_api_tournaments.py 2019 2024 2026
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.workflows.wta_api import build_wta_api_tournaments

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2026 2020-2025",
    )
    parser.add_argument(
        "--clean-dir",
        type=Path,
        default=None,
        help="Override the WTA-API tournament-table output directory (default: config-driven)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build/update the WTA-tournaments-API tournament-summary table for the specified years.

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

    logger.info("Building WTA-API tournaments, %d year(s): %s", len(years), ", ".join(map(str, years)))

    table_path, tournament_count = build_wta_api_tournaments(years, clean_dir=args.clean_dir)

    logger.info("%d tournament(s) in %s", tournament_count, table_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
