"""
Run Pass-1 match linking (tournament id + exact rank pair) for one tour/year(s).

Thin CLI wrapper around `tennis_data_pipeline.mapper.matches.build_rank_links` -
loads the clean UK/Sackmann match tables and the tournament source-links
crosswalk for the requested tour/years, links them, prints a coverage summary,
and optionally writes the three resulting tables (accepted/ambiguous/unmatched)
to CSV.

This is Pass 1 only - tournament-blocked exact rank pair, no player-name
matching yet (see `Link-UK-Sackmann.ipynb` for the full planned pass sequence).

Usage:
    python scripts/mapper/link_matches.py --tour atp 2025
    python scripts/mapper/link_matches.py --tour atp 2015-2025
    python scripts/mapper/link_matches.py --tour wta 2024 2025 --output-dir data/mapping/matches
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.datasources import sackmann as sk
from tennis_data_pipeline.loader.mapper import load_tournament_source_links
from tennis_data_pipeline.loader.uk import load_clean_uk_data_range
from tennis_data_pipeline.mapper.matches import build_rank_links

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
        help="Override the tournament mapping directory (default: config-driven, data/mapping)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Write accepted/ambiguous/unmatched CSVs here (default: don't write, just print a summary)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def _log_summary(
    tour: str, years: list[int], uk_total: int, accepted: int, ambiguous: int, unmatched: int
) -> None:
    coverage = accepted / uk_total if uk_total else 0.0
    logger.info(
        "[%s %s] uk_matches=%d accepted=%d (%.1f%%) ambiguous=%d unmatched=%d",
        tour.upper(),
        ", ".join(map(str, years)),
        uk_total,
        accepted,
        coverage * 100,
        ambiguous,
        unmatched,
    )


def main(argv: list[str] | None = None) -> int:
    """Link one tour's UK<->Sackmann matches for the specified years via Pass 1.

    Returns:
        Exit code: 0 on success, 2 on an argument parsing error.
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

    sk_tour = sk.atp if args.tour == "atp" else sk.wta

    logger.info("Loading %s UK matches, %d year(s): %s", args.tour.upper(), len(years), years)
    uk_df = load_clean_uk_data_range(args.tour, years)

    logger.info("Loading %s Sackmann matches", args.tour.upper())
    sackmann_df = sk_tour.load_years(years)

    logger.info("Loading %s tournament source links", args.tour.upper())
    tournament_mapper_df = load_tournament_source_links(args.tour, args.mapping_dir)

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, tournament_mapper_df)
    _log_summary(args.tour, years, len(uk_df), len(accepted), len(ambiguous), len(unmatched))

    if args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        accepted.to_csv(args.output_dir / f"{args.tour}_rank_links_accepted.csv", index=False)
        ambiguous.to_csv(args.output_dir / f"{args.tour}_rank_links_ambiguous.csv", index=False)
        unmatched.to_csv(args.output_dir / f"{args.tour}_rank_links_unmatched.csv", index=False)
        logger.info("Wrote accepted/ambiguous/unmatched CSVs to %s", args.output_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
