"""Weekly Tennis-Data UK refresh: fetch, clean, and rebuild tournaments - unattended-safe.

Thin CLI wrapper around `tennis_data_pipeline.workflows.uk.update_current_season`
- all the actual fetch/clean/tournament logic lives in the package, this script
just parses args, runs it, logs the report, and picks an exit code.

Meant to be run on a schedule (e.g. a weekly GitHub Action). Every tour/year is
handled best-effort:

- A download failure (site down, or the new season isn't published yet) is
  logged as a warning and does not fail the run - it's expected to happen and
  self-heals next time the job runs.
- A clean failure (a new tournament-consistency issue, reused id, or other
  data-quality problem) is logged as an error - it almost certainly needs a
  new entry in `handler/uk/cleaner/known_fixes/` or a `KNOWN_*_YEARS`
  exception, so the run exits non-zero to make CI flag it.

Defaults to the current year plus the previous one, so late-finalized data
from last season and a not-yet-published new season are both handled without
extra flags.

Usage:
    python scripts/uk/weekly_update.py
    python scripts/uk/weekly_update.py --tour atp
    python scripts/uk/weekly_update.py --years 2025 2026
    python scripts/uk/weekly_update.py --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.workflows.uk import (
    log_season_update_report,
    update_current_season,
)

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-t",
        "--tour",
        choices=_TOURS,
        action="append",
        dest="tours",
        help="Tour to update (repeatable, e.g. -t atp -t wta). Default: both.",
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs="+",
        default=None,
        help="Years to update (default: current year + previous year).",
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
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the weekly update and return an exit code (0 = OK, 1 = needs attention).

    Args:
        argv: Optional list of command-line arguments to parse. If None, defaults to sys.argv.

    """
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    report = update_current_season(
        tours=args.tours or _TOURS,
        years=args.years,
        raw_dir=args.raw_dir,
        clean_dir=args.clean_dir,
    )
    log_season_update_report(report)

    return 1 if report.needs_attention else 0


if __name__ == "__main__":
    sys.exit(main())
