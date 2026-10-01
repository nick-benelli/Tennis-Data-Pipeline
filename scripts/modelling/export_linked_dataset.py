"""Export the curated Sackmann+UK linked match dataset for use in another repo.

Thin CLI wrapper around `tennis_data_pipeline.workflows.modelling.build_match_dataset`
- the actual column-selection/merge logic lives in the package (see
  `workflows/modelling/dataset.py` and notebooks/dev/explore-linked-data.ipynb's
  "Feature audit" cells for the reasoning) so it's reusable outside this
  script too.

Writes one file per tour+year to
<output-dir>/data/clean/matches/<tour>/sackmann_uk_<tour>_<year>_matches.<ext>
(see `_RELATIVE_PATH_TEMPLATE`). Parquet (default) preserves the nullable
Int64/boolean/category/string dtypes exactly; CSV does not.

Every row is kept, including the `data_quality_flag`-flagged ones - filter
those downstream instead of baking that decision in here.

`<output-dir>` is the destination repo's root - machine-specific, so it's
never hardcoded: pass `--output-dir`, or set `TENNIS_ML_EXPORT_DIR` in a
`.env` file (see `.env.template`) - `.env` itself is gitignored, so the path
never ends up in the public repo.

Usage:
    python scripts/modelling/export_linked_dataset.py
    python scripts/modelling/export_linked_dataset.py --tour atp 2015-2020
    python scripts/modelling/export_linked_dataset.py --format csv --output-dir /tmp/out
    python scripts/modelling/export_linked_dataset.py --chronological
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from tennis_data_pipeline.cli import parse_years
from tennis_data_pipeline.datasources.sackmann.client import Tour
from tennis_data_pipeline.workflows.modelling import build_match_dataset, discover_available_years

logger = logging.getLogger(__name__)

_TOURS = ("atp", "wta")
_OUTPUT_DIR_ENV_VAR = "TENNIS_ML_EXPORT_DIR"
# Relative to --output-dir/$TENNIS_ML_EXPORT_DIR (the destination repo's root).
_RELATIVE_PATH_TEMPLATE = "data/raw/matches/{tour}/sackmann_uk_{tour}_{year}_matches"


def _env_default_output_dir() -> Path | None:
    """Read `TENNIS_ML_EXPORT_DIR` from the environment/.env, if set."""
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path if dotenv_path else None)

    value = os.getenv(_OUTPUT_DIR_ENV_VAR)
    return Path(value).expanduser() if value else None


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
        help="Tour(s) to export (default: both atp and wta)",
    )
    parser.add_argument(
        "years",
        nargs="*",
        help="One or more years and/or ranges, e.g. 2024 2019 2000-2015 "
        "(default: every year with a data/linked/<tour>/<year>/ output)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=f"Destination root directory (default: ${_OUTPUT_DIR_ENV_VAR} from .env)",
    )
    parser.add_argument(
        "--format",
        choices=("parquet", "csv"),
        default="parquet",
        help="Output file format (default: parquet)",
    )
    parser.add_argument(
        "--chronological",
        action="store_true",
        help="Order matches chronologically instead of the raw archive's final-to-first-round order",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args(argv)
    if args.output_dir is None:
        args.output_dir = _env_default_output_dir()
        if args.output_dir is None:
            parser.error(
                f"No --output-dir given and {_OUTPUT_DIR_ENV_VAR} isn't set "
                f"(add it to your .env file, or pass --output-dir explicitly)"
            )
    return args


def _write(df, path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "parquet":
        df.to_parquet(path, index=False)
    else:
        df.to_csv(path, index=False)


def main(argv: list[str] | None = None) -> int:
    """Export the curated Sackmann+UK linked dataset for the requested tour(s)/year(s).

    Args:
        argv: Optional list of command-line arguments to parse. If None, defaults to sys.argv.

    Returns:
        Exit code: 0 on success (even if some tour/year combos failed - see the logged
        summary), 2 if there was an argument parsing error.

    """
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        requested_years = parse_years(args.years) if args.years else None
    except argparse.ArgumentTypeError as exc:
        logger.error("Invalid year argument: %s", exc)
        return 2

    tours = [Tour(t) for t in (args.tours or _TOURS)]
    ext = "parquet" if args.format == "parquet" else "csv"

    written = 0
    failed: list[str] = []
    for tour in tours:
        years = requested_years if requested_years is not None else discover_available_years(tour)
        if not years:
            logger.warning("%s: no available years found, skipping", tour.value.upper())
            continue

        for year in years:
            try:
                df = build_match_dataset(tour, year, chronological=args.chronological)
            except Exception:
                logger.exception("%s %d: failed to build dataset", tour.value.upper(), year)
                failed.append(f"{tour.value}_{year}")
                continue

            relative_path = _RELATIVE_PATH_TEMPLATE.format(tour=tour.value, year=year)
            out_path = args.output_dir / f"{relative_path}.{ext}"
            _write(df, out_path, args.format)
            logger.info("%s %d: wrote %d rows to %s", tour.value.upper(), year, len(df), out_path)
            written += 1

    logger.info("Done: %d file(s) written, %d failed", written, len(failed))
    if failed:
        logger.warning("Failed tour/year combos: %s", ", ".join(failed))

    return 0


if __name__ == "__main__":
    sys.exit(main())
