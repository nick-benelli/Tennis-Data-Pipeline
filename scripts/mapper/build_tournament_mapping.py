"""
Build/update the cross-source (Tennis-Data UK <-> Sackmann <-> ATP) tournament id mapping.

Thin CLI wrapper around `tennis_data_pipeline.workflows.mapper.build_tournament_mapping`
- the actual matching logic lives in `mapper/tournaments.py` (pure, testable),
  and the I/O/upsert logic lives in `workflows/mapper/tournaments.py`, so both
  are reusable outside this script too.

Requires both tours' tournament-summary tables to already exist for every
requested year (see `scripts/uk/build_uk_tournaments.py` and
`scripts/sackmann/build_sackmann_tournaments.py`); a year missing either table
is skipped with a warning.

Writes/updates two growable reference tables under
data/mapping/tournaments/<tour>_tournament_crosswalk.csv and
<tour>_tournament_source_links.csv. Existing rows in both files always win
over freshly computed ones - hand corrections made directly in the CSVs are
the source of truth and are never overwritten by rerunning this script.

Any matched pair scoring below --review-threshold is printed for manual
review; nothing is auto-rejected, but a weak match is worth double-checking
(and hand-correcting in the crosswalk/source-links CSVs if it's wrong) before
relying on it downstream.

Usage:
    python scripts/mapper/build_tournament_mapping.py --tour atp 2025
    python scripts/mapper/build_tournament_mapping.py --tour atp 2010-2025
    python scripts/mapper/build_tournament_mapping.py --tour wta 2024 2025 --review-threshold 0.95
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.workflows.mapper import build_tournament_mapping

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")
_DEFAULT_REVIEW_THRESHOLD = 0.9


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-t", "--tour", choices=_TOURS, required=True, help="Tour to map")
    parser.add_argument(
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2022 2019 2010-2015",
    )
    parser.add_argument(
        "--review-threshold",
        type=float,
        default=_DEFAULT_REVIEW_THRESHOLD,
        help=(
            "Print matched pairs scoring below this for manual review "
            f"(default: {_DEFAULT_REVIEW_THRESHOLD})"
        ),
    )
    parser.add_argument(
        "--uk-clean-dir",
        type=Path,
        default=None,
        help="Override the UK Stage-4 clean checkpoint directory (default: config-driven)",
    )
    parser.add_argument(
        "--sackmann-clean-dir",
        type=Path,
        default=None,
        help="Override the Sackmann clean checkpoint directory (default: config-driven)",
    )
    parser.add_argument(
        "--wta-api-clean-dir",
        type=Path,
        default=None,
        help="Override the WTA-tournaments-API clean checkpoint directory (default: config-driven)",
    )
    parser.add_argument(
        "--mapping-dir",
        type=Path,
        default=None,
        help="Override the mapping output directory (default: config-driven, data/mapping)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Build/update the tournament id mapping for the specified tour and years.

    Args:
        argv: Optional list of command-line arguments to parse. If None, defaults to sys.argv.

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
        "Mapping %s tournaments, %d year(s): %s",
        args.tour.upper(),
        len(years),
        ", ".join(map(str, years)),
    )

    succeeded = 0
    for year in years:
        try:
            result = build_tournament_mapping(
                args.tour,
                year,
                uk_clean_dir=args.uk_clean_dir,
                sackmann_clean_dir=args.sackmann_clean_dir,
                wta_api_clean_dir=args.wta_api_clean_dir,
                mapping_dir=args.mapping_dir,
            )
        except FileNotFoundError as exc:
            logger.warning("[%s %s] Skipped: %s", args.tour.upper(), year, exc)
            continue

        succeeded += 1
        logger.info(
            "[%s %s] Matched %d/%d UK and %d/%d Sackmann tournaments",
            args.tour.upper(),
            year,
            result.matched_count,
            result.uk_total,
            result.matched_count,
            result.sackmann_total,
        )

        weak = result.review_df.loc[result.review_df["score"] < args.review_threshold]
        if not weak.empty:
            logger.warning(
                "[%s %s] %d matched pair(s) scored below %.2f - review before trusting:\n%s",
                args.tour.upper(),
                year,
                len(weak),
                args.review_threshold,
                weak.to_string(index=False),
            )

        if result.wta_api_review_df is not None and not result.wta_api_review_df.empty:
            weak_wta_api = result.wta_api_review_df.loc[
                result.wta_api_review_df["score"] < args.review_threshold
            ]
            if not weak_wta_api.empty:
                logger.warning(
                    "[%s %s] %d Sackmann<->WTA-API backfill pair(s) scored below %.2f - review "
                    "before trusting:\n%s",
                    args.tour.upper(),
                    year,
                    len(weak_wta_api),
                    args.review_threshold,
                    weak_wta_api.to_string(index=False),
                )

    if succeeded == 0:
        logger.error("No years were successfully mapped.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
