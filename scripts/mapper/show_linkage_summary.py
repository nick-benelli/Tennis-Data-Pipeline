"""
Print the UK<->Sackmann match-linkage coverage/health summary for one tour.

Thin CLI reader around `data/linked/<tour>/<tour>_linkage_summary.csv` (see
`tennis_data_pipeline.loader.linked.all_years_summary_path`) - one row per
year, written by `scripts/mapper/link_matches_uk_sackmann.py`.

With no years given, every row is printed. Otherwise only the requested
year(s)/range(s) are shown (missing years are reported, not silently dropped).

By default only the columns that matter for a quick terminal glance are
shown, with short names (`tour`/`linked_manual`/`linked_pass_1`/
`linked_pass_2`/`linked_at` are dropped); pass --full for every column with
its original name.

Usage:
    python scripts/mapper/show_linkage_summary.py --tour atp
    python scripts/mapper/show_linkage_summary.py --tour atp 2023
    python scripts/mapper/show_linkage_summary.py --tour atp 2010-2015
    python scripts/mapper/show_linkage_summary.py --tour wta 2019 2021 2023-2025
    python scripts/mapper/show_linkage_summary.py --tour atp 2023 --full
"""

from __future__ import annotations

import argparse
import logging
import sys

import pandas as pd

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.loader.linked import all_years_summary_path

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")

# Short display names for every column - `tour` is dropped by default since
# it's already implied by --tour/the header line above the table.
_SHORT_NAMES = {
    "uk_total_matches": "uk",
    "sackmann_total_matches": "sackmann",
    "linked_matches": "linked",
    "linked_manual": "manual",
    "linked_pass_1": "pass1",
    "linked_pass_2": "pass2",
    "ambiguous_matches": "ambig",
    "unmatched_matches": "unmatched",
    "coverage_pct": "coverage",
}
# Columns shown in the compact (default) view - drops the pass1/pass2/manual
# breakdown and the linked_at timestamp, which matter for debugging but not
# for a quick glance.
_COMPACT_COLUMNS = [
    "year",
    "uk_total_matches",
    "sackmann_total_matches",
    "linked_matches",
    "ambiguous_matches",
    "unmatched_matches",
    "coverage_pct",
]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-t", "--tour", choices=_TOURS, required=True, help="Tour to display")
    parser.add_argument(
        "years",
        nargs="*",
        help="Optional year(s) and/or range(s) to filter to, e.g. 2022 2019 2010-2015 "
        "(default: show every year)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Show every column (tour, linked_manual/pass_1/pass_2, linked_at) instead of "
        "the compact default view",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print one tour's all-years linkage summary table, optionally filtered to specific years.

    Returns:
        Exit code: 0 on success, 2 on an argument/parsing error, 1 if the
        summary file is missing or no requested year has a row.

    """
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )

    try:
        years = parse_years(args.years) if args.years else None
    except argparse.ArgumentTypeError as exc:
        logger.error("Invalid year argument: %s", exc)
        return 2

    path = all_years_summary_path(args.tour)
    if not path.exists():
        logger.error(
            "No linkage summary found for %s at %s (run link_matches_uk_sackmann.py first)",
            args.tour.upper(),
            path,
        )
        return 1

    df = pd.read_csv(path)

    if years is not None:
        missing = sorted(set(years) - set(df["year"]))
        if missing:
            logger.warning("No summary row for %s year(s): %s", args.tour.upper(), missing)
        df = df[df["year"].isin(years)]

    if df.empty:
        logger.error("No matching rows to display.")
        return 1

    df = df.sort_values("year").reset_index(drop=True)
    df["coverage_pct"] = df["coverage_pct"].map(lambda pct: f"{pct:.1f}%")
    df["linked_at"] = pd.to_datetime(df["linked_at"]).dt.strftime("%Y-%m-%d %H:%M")

    if not args.full:
        df = df[_COMPACT_COLUMNS]
    df = df.rename(columns=_SHORT_NAMES)

    print(f"\n{args.tour.upper()} linkage summary ({path})\n")
    print(df.to_string(index=False))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
