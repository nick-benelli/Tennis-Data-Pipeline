"""
Run Pass 0 + Pass 1 + Pass 2 match linking (hand-maintained manual overrides
first, then tournament id + rank pair, then tournament + round + name pair)
for one tour/year(s), and persist the formalized outputs.

Thin CLI wrapper around `tennis_data_pipeline.workflows.mapper.build_match_links`
- the actual linking logic lives in `mapper/matches/uk_sackmann/` (pure,
  testable), and the I/O logic lives in `workflows/mapper/matches/uk_sackmann.py`,
  so both are reusable outside this script too.

Requires that year's clean UK match CSV to already exist (see
`scripts/uk/clean_uk_data.py`); a year missing it is skipped with a warning.

Writes/updates five tables per year under data/linked/<tour>/<year>/:
`<tour>_match_links_{year}.csv` (compact lineage crosswalk),
`<tour>_matches_enriched_{year}.csv` (analysis-ready UK matches + linkage
columns), `<tour>_linkage_summary_{year}.csv` (one coverage/health row), and
under `review/`: `<tour>_linkage_ambiguous_{year}.csv` /
`<tour>_linkage_unmatched_{year}.csv` (the pipeline's final residuals). Each
year is overwritten independently; other years are never touched.

Usage:
    python scripts/mapper/link_matches_uk_sackmann.py --tour atp 2025
    python scripts/mapper/link_matches_uk_sackmann.py --tour atp 2010-2025
    python scripts/mapper/link_matches_uk_sackmann.py --tour wta 2024 2025
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.workflows.mapper import build_match_links

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
    parser.add_argument("-t", "--tour", choices=_TOURS, required=True, help="Tour to link")
    parser.add_argument(
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2022 2019 2010-2015",
    )
    parser.add_argument(
        "--mapping-dir",
        type=Path,
        default=None,
        help="Override the mapping directory (default: config-driven, data/mapping)",
    )
    parser.add_argument(
        "--linked-dir",
        type=Path,
        default=None,
        help="Override the linked-output directory (default: config-driven, data/linked)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Link one tour's UK<->Sackmann matches for the specified years via Pass 1.

    Returns:
        Exit code: 0 on success (even if some years were skipped), 2 on an
        argument parsing error, 1 if every requested year failed/was skipped.

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
        "Linking %s matches, %d year(s): %s", args.tour.upper(), len(years), ", ".join(map(str, years))
    )

    succeeded = 0
    for year in years:
        try:
            result = build_match_links(
                args.tour, year, mapping_dir=args.mapping_dir, linked_dir=args.linked_dir
            )
        except FileNotFoundError as exc:
            logger.warning("[%s %s] Skipped: %s", args.tour.upper(), year, exc)
            continue

        succeeded += 1
        coverage = result.linked_count / result.uk_total if result.uk_total else 0.0
        logger.info(
            "[%s %s] uk_matches=%d linked=%d (pass1=%d pass2=%d) ambiguous=%d "
            "unmatched=%d (%.1f%% coverage) -> %s",
            args.tour.upper(),
            year,
            result.uk_total,
            result.linked_count,
            result.linked_pass_1,
            result.linked_pass_2,
            result.ambiguous_count,
            result.unmatched_count,
            coverage * 100,
            result.output_dir,
        )

    if succeeded == 0:
        logger.error("No years were successfully linked.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
