"""Daily/full-history update for Tennis-Data.co.uk match data.

Mirrors the workflow from notebooks/wta-tennis-daily-update.ipynb (build full
history if no dataset exists yet, otherwise refresh just the current season
and upsert it), but reuses tennis_data_pipeline's client/cleaning code instead
of reimplementing HTTP, retries, and column cleaning here.

Unlike the notebook, this does not reorient matches into Player_1/Player_2 or
derive betting-market columns (Odd_1/Odd_2, Score) - the output stays in the
package's source-faithful winner_/loser_ schema.

Usage:
    python scripts/call_tennis_data_uk.py --tour wta --output data/clean/tennis-data-uk/wta_daily.csv
    python scripts/call_tennis_data_uk.py --tour atp --output data/clean/tennis-data-uk/atp_daily.csv --start-year 2000
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


def _load_full_history(tour_module, start_year: int, end_year: int) -> pd.DataFrame:
    """Download every season in range, skipping any single year that fails."""
    frames: list[pd.DataFrame] = []

    for year in range(start_year, end_year + 1):
        try:
            frames.append(tour_module.load_year(year))
        except Exception as exc:  # noqa: BLE001 - a bad season should not abort the rest
            print(f"Skipped {year}: {exc}")

    if not frames:
        raise RuntimeError(f"No seasons could be downloaded for {start_year}-{end_year}.")

    return pd.concat(frames, ignore_index=True)


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
    start_year: int | None = None,
    year: int | None = None,
) -> pd.DataFrame:
    """Refresh a Tennis-Data UK dataset for one tour and persist it to CSV."""
    tour_module = _TOUR_MODULES[tour]
    year = year or dt.datetime.now().astimezone().year
    start_year = start_year or _DEFAULT_START_YEAR[tour]

    existing = _read_existing(output_path)

    if existing.empty:
        print(f"No existing dataset at {output_path}; downloading full history {start_year}-{year}.")
        final = _load_full_history(tour_module, start_year, year)
    else:
        print(f"Found existing dataset at {output_path} ({len(existing):,} rows); refreshing {year}.")

        try:
            updated_year = tour_module.load_year(year)
        except Exception as exc:  # noqa: BLE001 - keep the existing dataset on refresh failure
            print(f"Failed to refresh {year}: {exc}. Keeping existing dataset unchanged.")
            final = existing
        else:
            final = _upsert_year(existing, updated_year, year)

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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tour", choices=sorted(_TOUR_MODULES), default="wta")
    parser.add_argument("--output", required=True, type=Path, help="CSV path to read/write")
    parser.add_argument(
        "--start-year",
        type=int,
        default=None,
        help="First season to download when no dataset exists yet (default: 2000 for ATP, 2007 for WTA)",
    )
    parser.add_argument("--year", type=int, default=None, help="Season to refresh (default: current year)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    update_dataset(args.tour, args.output, start_year=args.start_year, year=args.year)


if __name__ == "__main__":
    main()

