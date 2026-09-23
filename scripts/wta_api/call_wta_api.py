"""Download WTA-tournaments-API season(s) and write them to the raw checkpoint.

Where/how snapshots are named comes entirely from config (configs/config.yaml's
`wta_api.raw_dir_name`/`raw_filename_template`) - this script only decides
*which* season(s) to fetch, and whether to persist the result at all.

Every tournament level is included (ITF through Grand Slam) - the raw
checkpoint preserves the API's own columns unmodified (see
`datasources.wta.cleaner.flatten_tournament`); filtering to main-tour-only is
a downstream concern.

Usage:
    python scripts/wta_api/call_wta_api.py 2026
    python scripts/wta_api/call_wta_api.py 2020-2026
    python scripts/wta_api/call_wta_api.py 2019 2024 2026

    # Dry run: download and report row counts, but don't write the checkpoint.
    python scripts/wta_api/call_wta_api.py 2026 --no-write
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tennis_data_pipeline.datasources.wta import WtaApiClient
from tennis_data_pipeline.workflows.wta_api import fetch_and_checkpoint_year

logger = logging.getLogger(__name__)


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
        "years",
        nargs="+",
        help="One or more years and/or ranges, e.g. 2026 2020-2025",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=None,
        help="Override the raw checkpoint output directory (default: config-driven)",
    )
    parser.add_argument(
        "--write",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write the raw snapshot checkpoint (default: True; use --no-write for a dry run)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Download/checkpoint the resolved season(s).

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

    client = WtaApiClient()
    for year in years:
        if args.write:
            path = fetch_and_checkpoint_year(year, client=client, raw_dir=args.raw_dir)
            print(f"[{year}] wrote snapshot to {path}")
        else:
            df = client.get_tournaments(year)
            print(f"[{year}] downloaded {len(df):,} rows (not written; --no-write)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
