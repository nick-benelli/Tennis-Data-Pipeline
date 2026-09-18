"""Daily/full-history update for Tennis-Data.co.uk match data.

Mirrors the workflow from notebooks/wta-tennis-daily-update.ipynb (build full
history if no dataset exists yet, otherwise refresh just the current season
and upsert it), but reuses tennis_data_pipeline's client/cleaning code instead
of reimplementing HTTP, retries, and column cleaning here.

Unlike the notebook, this does not reorient matches into Player_1/Player_2 or
derive betting-market columns (Odd_1/Odd_2, Score) - the output stays in the
package's source-faithful winner_/loser_ schema.

Usage:
    # Default: bootstrap full history if --output doesn't exist yet, otherwise refresh the current year.
    python scripts/call_tennis_data_uk.py --tour wta --output data/clean/tennis-data-uk/wta_daily.csv

    # Refresh/backfill a single season.
    python scripts/call_tennis_data_uk.py --tour atp --output data/clean/tennis-data-uk/atp_daily.csv --year 2023

    # Refresh/backfill a range of seasons (--end-year defaults to --year or the current year).
    python scripts/call_tennis_data_uk.py --tour atp --output data/clean/tennis-data-uk/atp_daily.csv --start-year 2000 --end-year 2010

    # Range plus an extra out-of-range season, e.g. backfill 2015-2020 and also refresh 2023.
    python scripts/call_tennis_data_uk.py --tour atp --output data/clean/tennis-data-uk/atp_daily.csv --start-year 2015 --end-year 2020 --year 2023
"""

from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd

from tennis_data_pipeline.datasources.tennis_data_uk import atp, wta

_TOUR_MODULES = {"atp": atp, "wta": wta}
_DEFAULT_START_YEAR = {"atp": 2000, "wta": 2007}

# Identifies a single match; mirrors the notebook's dedup key but keeps
# winner/loser orientation instead of Player_1/Player_2.
_DEDUP_COLUMNS = ["Date", "Tournament", "Round", "winner_Name", "loser_Name"]


def _resolve_years(
    tour: str,
    *,
    year: int | None,
    start_year: int | None,
    end_year: int | None,
    existing_is_empty: bool,
) -> list[int]:
    """Turn --year/--start-year/--end-year into the sorted list of seasons to fetch."""
    current_year = dt.datetime.now().astimezone().year
    years: set[int] = set()

    if start_year is not None or end_year is not None:
        range_start = start_year if start_year is not None else _DEFAULT_START_YEAR[tour]
        range_end = end_year if end_year is not None else (year or current_year)
        years.update(range(range_start, range_end + 1))

    if year is not None:
        years.add(year)

    if not years:
        # No years given: bootstrap full history for a new dataset, or just refresh
        # the current season for one that already exists (the old daily-update behavior).
        if existing_is_empty:
            years.update(range(_DEFAULT_START_YEAR[tour], current_year + 1))
        else:
            years.add(current_year)

    return sorted(years)


def _read_existing(output_path: Path) -> pd.DataFrame:
    if not output_path.exists():
        return pd.DataFrame()

    existing = pd.read_csv(output_path, low_memory=False)

    if "Date" in existing.columns:
        existing["Date"] = pd.to_datetime(existing["Date"], errors="coerce")

    return existing


def _upsert_year(existing: pd.DataFrame, updated_year: pd.DataFrame, year: int) -> pd.DataFrame:
    """Replace `year`'s rows in `existing` with the freshly downloaded ones."""
    if existing.empty:
        return updated_year

    kept = existing[existing["Date"].dt.year.ne(year)]

    return pd.concat([kept, updated_year], ignore_index=True)


def update_dataset(
    tour: str,
    output_path: Path,
    *,
    year: int | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Download/refresh one or more Tennis-Data UK seasons and persist the dataset to CSV."""
    tour_module = _TOUR_MODULES[tour]
    existing = _read_existing(output_path)

    years = _resolve_years(
        tour,
        year=year,
        start_year=start_year,
        end_year=end_year,
        existing_is_empty=existing.empty,
    )
    print(f"Fetching {tour.upper()} seasons: {years[0]}-{years[-1]} ({len(years)} season(s)).")

    final = existing

    for season in years:
        try:
            downloaded = tour_module.load_year(season)
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            print(f"Skipped {season}: {exc}")
            continue

        final = _upsert_year(final, downloaded, season)

    if final.empty:
        raise RuntimeError(f"No seasons could be downloaded for {tour.upper()} {years[0]}-{years[-1]}.")

    rows_before = len(final)
    final = final.drop_duplicates(subset=_DEDUP_COLUMNS, keep="last")
    final = final.sort_values(
        ["Date", "Tournament", "Round", "winner_Name", "loser_Name"],
        na_position="last",
    ).reset_index(drop=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(output_path, index=False)

    print(
        f"Rows before dedup: {rows_before:,} | after: {len(final):,} "
        f"| dropped duplicates: {rows_before - len(final):,}"
    )
    print(f"Wrote {output_path} ({len(final):,} rows).")

    return final


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tour", choices=sorted(_TOUR_MODULES), default="wta", help="Tour to download (default: wta)")
    parser.add_argument("--output", required=True, type=Path, help="CSV path to read/write")
    parser.add_argument("--year", type=int, default=None, help="Single season to download/refresh")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="First season of a range to download/refresh (default: 2000 for ATP, 2007 for WTA)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=None,
        help="Last season of a range to download/refresh (default: --year, or the current year)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args and run the dataset update."""
    args = _parse_args(argv)
    update_dataset(
        args.tour,
        args.output,
        year=args.year,
        start_year=args.start_year,
        end_year=args.end_year,
    )


if __name__ == "__main__":
    main()
