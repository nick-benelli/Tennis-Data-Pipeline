"""Clean Tennis-Data UK ATP season CSVs (raw -> validated -> clean) from the CLI.

Ports notebooks/cleaning/uk-data-cleaning.ipynb into a repeatable batch job:
loads one or more raw seasons, applies the known data-error fixes verified in
that notebook, runs them through `clean_uk_atp_data`, appends to the running
quality report, and writes the clean CSV per year. Each year is processed
independently: one bad season is logged and skipped rather than aborting the
whole batch (use --fail-fast to change that).

Usage:
    python scripts/uk/clean_uk_atp_data.py 2022
    python scripts/uk/clean_uk_atp_data.py 2019 2015 2013
    python scripts/uk/clean_uk_atp_data.py 2010-2023
    python scripts/uk/clean_uk_atp_data.py 2000-2009 2015 2020-2023 --verbose
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tennis_data_pipeline.handler.uk.cleaner.atp import (
    build_uk_atp_quality_report,
    clean_uk_atp_data,
)
from tennis_data_pipeline.handler.uk.validatior.tournaments import (
    find_uk_inconsistent_tournaments,
    find_uk_reused_tournament_ids,
)

logger = logging.getLogger(__name__)

# scripts/uk/clean_uk_atp_data.py -> repo root is two levels up.
DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = "data/raw/tennis-data-uk/2024-10/atp"
CLEAN_DATA_DIR = "data/clean/tennis-data-uk/atp"
QUALITY_REPORT_PATH = "data/clean/tennis-data-uk/atp/analysis/uk_atp_quality_report.csv"

# Years where find_uk_inconsistent_tournaments flags known, already-reviewed issues.
YEARS_WITH_KNOWN_TOURNAMENT_INCONSISTENCIES = {2023}

ATP_BEST_OF_5_TOURNAMENTS = {
    "Australian Open",
    "French Open",
    "Roland Garros",
    "Wimbledon",
    "US Open",
}

RAW_ODDS_COLS = ["B365W", "B365L", "PSW", "PSL", "MaxW", "MaxL", "AvgW", "AvgL"]


# --------------------------------------------------------------------------- #
# Load + known-issue fixes
# --------------------------------------------------------------------------- #

def load_dirty_uk_atp_data(project_dir: Path, year: int) -> pd.DataFrame:
    """Load one season's raw Tennis-Data UK ATP CSV with basic dtypes applied."""
    path = project_dir / RAW_DATA_DIR / f"atp_singles_results_{year}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No raw data file for {year}: {path}")

    df = pd.read_csv(path)

    # Date format drifts across seasons (e.g. "1/1/23" vs. "2000-01-03").
    df["Date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=False)
    df["Year"] = year

    # Nullable ints: ranks/points/set-scores are whole numbers but can be missing (e.g. retired matches).
    int_cols = [
        "ATP", "Year", "Best of",
        "WRank", "LRank", "WPts", "LPts",
        "W1", "L1", "W2", "L2", "W3", "L3", "W4", "L4", "W5", "L5",
        "Wsets", "Lsets",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Everything left over is bookmaker odds; which bookmakers are present varies by year.
    known_cols = {
        "ATP", "Year", "Location", "Tournament", "Date", "Series", "Court",
        "Surface", "Round", "Best of", "Winner", "Loser", "Comment", *int_cols,
    }
    odds_cols = [col for col in df.columns if col not in known_cols]
    df[odds_cols] = df[odds_cols].apply(pd.to_numeric, errors="coerce")

    for col in ["Series", "Court", "Surface", "Round", "Comment"]:
        if col in df.columns:
            df[col] = df[col].astype("category")

    return df


def apply_known_best_of_fixes(df: pd.DataFrame) -> pd.DataFrame:
    """Correct raw 'Best of' values the source mislabels or omits entirely."""
    df = df.copy()

    # All ATP Grand Slams are best-of-5; the raw source mislabels some individual matches.
    grand_slam_mask = df["Tournament"].isin(ATP_BEST_OF_5_TOURNAMENTS)
    df.loc[grand_slam_mask, "Best of"] = 5

    # ATP Finals (Masters Cup) is best-of-3 for every round; the raw source omits
    # "Best of" entirely for these rows rather than mislabeling it.
    masters_cup_mask = df["Series"] == "Masters Cup"
    df.loc[masters_cup_mask & df["Best of"].isna(), "Best of"] = 3

    return df


def fix_bad_odds(df: pd.DataFrame) -> pd.DataFrame:
    """Null out impossible (<1.0) decimal odds instead of guessing the intended value."""
    df = df.copy()

    for col in RAW_ODDS_COLS:
        if col not in df.columns:
            continue
        bad_odds = df[col] < 1
        if bad_odds.any():
            logger.warning("%s: nulling %d odds < 1", col, int(bad_odds.sum()))
            df.loc[bad_odds, col] = pd.NA

    return df


def _assert_single_match(mask: pd.Series, year: int, description: str) -> None:
    matched = int(mask.sum())
    if matched != 1:
        raise ValueError(
            f"Expected exactly 1 row for known fix '{description}' in {year}, "
            f"found {matched}. The raw source may have changed; review before "
            "re-applying this fix."
        )


def apply_known_match_fixes(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Apply one-off row fixes for raw data errors verified against real results.

    See notebooks/cleaning/uk-data-cleaning.ipynb "Bad Set-Score Checker" for
    the Wikipedia sources backing each of these.
    """
    df = df.copy()

    if year == 2019:
        # Metz final (Tsonga d. Bedene): corrupted set-2 score, missing set 3
        # entirely. Actual result was 6-7, 7-6, 6-3 to Tsonga.
        mask = (
            (df["ATP"] == 53)
            & (df["Winner"] == "Tsonga J.W.")
            & (df["Loser"] == "Bedene A.")
            & (df["Date"] == "2019-09-22")
        )
        _assert_single_match(mask, year, "Metz final (Tsonga d. Bedene)")
        df.loc[mask, ["W1", "L1", "W2", "L2", "W3", "L3"]] = [6, 7, 7, 6, 6, 3]
        df.loc[mask, ["Wsets", "Lsets"]] = [2, 1]

    if year == 2015:
        # Nottingham (AEGON Open) semifinal (Istomin d. Baghdatis): labeled
        # "Completed" despite only a single incomplete set (1-2) recorded;
        # Baghdatis retired.
        mask = (
            (df["ATP"] == 38)
            & (df["Winner"] == "Istomin D.")
            & (df["Loser"] == "Baghdatis M.")
            & (df["Date"] == "2015-06-26")
        )
        _assert_single_match(mask, year, "Nottingham semifinal (Istomin d. Baghdatis)")
        df.loc[mask, "Comment"] = "Retired"

    if year == 2013:
        # Bogota (Claro Open Colombia) final (Karlovic d. Falla): Wsets/Lsets
        # both recorded as 0 despite two straight sets being recorded. Actual
        # result was 6-3, 7-6 to Karlovic.
        mask = (
            (df["ATP"] == 41)
            & (df["Winner"] == "Karlovic I.")
            & (df["Loser"] == "Falla A.")
            & (df["Date"] == "2013-07-21")
        )
        _assert_single_match(mask, year, "Bogota final (Karlovic d. Falla)")
        df.loc[mask, ["Wsets", "Lsets"]] = [2, 0]

    return df


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def check_tournament_consistency(df: pd.DataFrame, year: int) -> None:
    """Raise if tournament metadata is inconsistent, unless `year` is a known exception."""
    if year in YEARS_WITH_KNOWN_TOURNAMENT_INCONSISTENCIES:
        logger.info("Skipping tournament-consistency check for %s (known exception).", year)
        return

    metrics, affected_rows = find_uk_inconsistent_tournaments(
        df,
        key_columns=["ATP", "Year", "Location"],
        info_cols=["Tournament", "Series", "Court", "Surface", "Best of"],
    )

    if not metrics.empty and not affected_rows.empty:
        raise ValueError(
            f"{len(metrics)} inconsistent tournament(s) found in {year} "
            f"({len(affected_rows)} row(s) affected)."
        )


def check_reused_tournament_ids(df: pd.DataFrame, year: int) -> None:
    """Raise if an ATP tournament id is reused across genuinely different tournaments."""
    metrics, affected_rows = find_uk_reused_tournament_ids(
        df=df, id_col="ATP", disambiguating_cols=["Location", "Tournament"],
    )

    if not metrics.empty and not affected_rows.empty:
        raise ValueError(
            f"{len(metrics)} reused ATP tournament id(s) found in {year} "
            f"({len(affected_rows)} row(s) affected)."
        )


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #

def update_quality_report(project_dir: Path, quality_report: pd.DataFrame) -> Path:
    """Merge one year's quality report into the running master report CSV."""
    report_path = project_dir / QUALITY_REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Accumulate one row per year across runs; re-running a year overwrites its old row.
    if report_path.exists():
        existing_report = pd.read_csv(report_path, index_col=0)
        combined_report = pd.concat([existing_report, quality_report])
        combined_report = combined_report[~combined_report.index.duplicated(keep="last")]
    else:
        combined_report = quality_report

    # Metrics where a missing value really means "zero".
    zero_fill_cols = [
        col
        for col in combined_report.columns
        if (
            col.startswith(("status_count_", "missing_pct_"))
            or col in {"duplicate_match_keys", "completed_missing_odds"}
        )
    ]
    combined_report[zero_fill_cols] = combined_report[zero_fill_cols].fillna(0)

    combined_report = combined_report.sort_values("year")
    combined_report = combined_report.round(4)
    combined_report.index.name = "index"

    combined_report.to_csv(report_path)
    return report_path


def write_clean_csv(project_dir: Path, year: int, df: pd.DataFrame) -> Path:
    csv_path = project_dir / CLEAN_DATA_DIR / f"uk_atp_singles_matches_{year}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    return csv_path


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def process_year(project_dir: Path, year: int) -> pd.DataFrame:
    """Run the full raw-to-clean pipeline for a single season and persist the output."""
    logger.info("[%s] Loading raw data", year)
    df = load_dirty_uk_atp_data(project_dir, year)

    logger.info("[%s] Applying known Best-of fixes", year)
    df = apply_known_best_of_fixes(df)

    logger.info("[%s] Checking tournament consistency", year)
    check_tournament_consistency(df, year)
    check_reused_tournament_ids(df, year)

    logger.info("[%s] Fixing bad odds", year)
    df = fix_bad_odds(df)

    logger.info("[%s] Applying known match fixes", year)
    df = apply_known_match_fixes(df, year)

    logger.info("[%s] Cleaning data", year)
    df_clean = clean_uk_atp_data(df)

    quality_report = build_uk_atp_quality_report(df_clean)
    report_path = update_quality_report(project_dir, quality_report)
    logger.info("[%s] Updated quality report at %s", year, report_path)

    csv_path = write_clean_csv(project_dir, year, df_clean)
    logger.info("[%s] Wrote %d rows to %s", year, len(df_clean), csv_path)

    return df_clean


@dataclass
class YearResult:
    year: int
    success: bool
    rows: int = 0
    error: str | None = None


def _log_summary(results: list[YearResult]) -> None:
    logger.info("=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    for result in results:
        if result.success:
            logger.info("  %s: OK (%d rows)", result.year, result.rows)
        else:
            logger.info("  %s: FAILED - %s", result.year, result.error)

    succeeded = sum(result.success for result in results)
    logger.info("%d/%d year(s) succeeded.", succeeded, len(results))


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
        help="One or more years and/or ranges, e.g. 2022 2019 2010-2015",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=DEFAULT_PROJECT_DIR,
        help="Repository root (default: inferred from this script's location)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first year that fails instead of processing the rest",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
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

    logger.info("Processing %d year(s): %s", len(years), ", ".join(map(str, years)))

    results: list[YearResult] = []
    for year in years:
        try:
            df_clean = process_year(args.project_dir, year)
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            logger.error("[%s] FAILED: %s", year, exc, exc_info=args.verbose)
            results.append(YearResult(year=year, success=False, error=str(exc)))
            if args.fail_fast:
                break
        else:
            results.append(YearResult(year=year, success=True, rows=len(df_clean)))

    _log_summary(results)

    return 0 if all(result.success for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
