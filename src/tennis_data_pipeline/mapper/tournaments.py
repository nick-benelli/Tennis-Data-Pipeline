"""Cross-source tournament id matching: Tennis-Data UK <-> Sackmann <-> permanent official tournament id.

Pure functions over already-clean tournament-summary `DataFrame`s (as produced by
`handler.uk.cleaner.tournaments.build_uk_tournament_table` and
`handler.sackmann.tournaments.build_sackmann_tournament_table`) - no file I/O here,
see `workflows.mapper.tournaments` for loading/persisting.

Background:
- Tennis-Data UK's `uk_tournament_id` resets 1-60 every season and isn't globally
  unique, so matching/persisting is keyed on `source_event_key` instead.
- Sackmann's `tourney_id` ("{year}-{tourney_number}") embeds the permanent official
  tournament id (the same id ATP.com/WTA.com use, shared across tours) in
  `tourney_number` for the vast majority of rows (verified: 1688/1745 non-Davis-Cup
  rows across 2000-2026) - see `extract_official_tournament_id`.
  Known exceptions: one 2016 Olympics row uses an `O16`-style code, and 2016-2020
  used an unrelated `M0xx` numbering scheme for ~13-14 Masters/500 events each of
  those years. Both parse to a blank id rather than a wrong one.
- Matching combines normalized name similarity (checked against both the UK
  sponsor name and the UK host-city location, since Sackmann uses the host city)
  with start-date proximity and surface match, then greedily assigns the
  best-scoring unique pairs; anything left over is kept unmatched (blank id)
  rather than forced.
- A hand-maintained `manual_matches` table can force a specific UK<->Sackmann
  pairing (or backfill an `official_tournament_id` the automatic extraction
  couldn't resolve, e.g. for the `M0xx`-era rows above) - see
  `match_uk_to_sackmann_tourneys`. Rows it covers are excluded from automatic
  matching entirely, so a rerun can never reconsider or reassign them.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, NamedTuple

import pandas as pd

MAX_DATE_DIFF_DAYS = 10  # same tournament shouldn't drift further than this between sources
MIN_MATCH_SCORE = 0.5  # candidates below this are treated as "no match"

# uk_tournament_id is deliberately excluded from the persisted shape - it's been
# unreliable across past years (resets 1-60 each season, reused/reshuffled ids).
LINK_COLUMNS = ["year", "uk_source_event_key", "sackmann_tourney_id"]


def normalize_tournament_name(name: str) -> str:
    """Lowercase, strip accents/punctuation so e.g. "Queen's Club" == "Queens Club"."""
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return name.strip()


def date_score(uk_start, sack_start, max_days: int = MAX_DATE_DIFF_DAYS) -> float:
    """Score based on how close two tournaments' start dates are.

    Args:
        uk_start: Start date of the UK tournament.
        sack_start: Start date of the Sackmann tournament.
        max_days: Diff (in days) at or beyond which the score bottoms out at 0.

    Returns:
        1.0 for the same day, decreasing linearly to 0.0 at `max_days` apart.

    """
    diff_days = abs((uk_start - sack_start).days)
    return max(0.0, 1 - diff_days / max_days)


def extract_official_tournament_id(sackmann_tourney_id: Any) -> Any:
    """Pull the permanent official tournament id out of a Sackmann `tourney_id`.

    Returns `pd.NA` for a missing input or a non-numeric `tourney_number`
    (Olympics/`M0xx`-era rows - see module docstring), never a guessed value.
    """
    if pd.isna(sackmann_tourney_id):
        return pd.NA
    number = str(sackmann_tourney_id).split("-", 1)[1]
    return int(number) if number.isdigit() else pd.NA


class TournamentMatchResult(NamedTuple):
    """Result of matching one tour+year's UK and Sackmann tournaments.

    `link_df` is the persisted crosswalk shape - `year`/`uk_source_event_key`/
    `sackmann_tourney_id`/`official_tournament_id`, one row per matched pair plus
    one row per unmatched UK or Sackmann tournament (blank on the other side).
    `review_df` is for manual eyeballing only (not persisted): `score`/
    `location`/`uk_name`/`sackmann_name` for every matched pair, weakest first.
    """

    link_df: pd.DataFrame
    review_df: pd.DataFrame
    uk_total: int
    sackmann_total: int
    matched_count: int
    manual_match_count: int = 0


MANUAL_MATCH_COLUMNS = [
    "year",
    "uk_source_event_key",
    "sackmann_tourney_id",
    "official_tournament_id",
]


def match_uk_to_sackmann_tourneys(
    df_uk_tourneys: pd.DataFrame,
    df_sackman_tourneys: pd.DataFrame,
    year: int,
    *,
    min_match_score: float = MIN_MATCH_SCORE,
    max_date_diff_days: int = MAX_DATE_DIFF_DAYS,
    manual_matches: pd.DataFrame | None = None,
) -> TournamentMatchResult:
    """Match one tour+season's UK tournaments to Sackmann tournaments.

    Both inputs should already be filtered to the target tour/year (and, for
    Sackmann, have Davis Cup excluded via `tourney_level != "D"`) - this function
    does no filtering of its own.

    `manual_matches` (optional) is a hand-maintained override table with columns
    `year`/`uk_source_event_key`/`sackmann_tourney_id`/`official_tournament_id`
    (any of the id columns may be blank on a given row). Filtered to `year`
    internally, so the caller can pass the whole multi-year file as-is. Two uses:

    1. Force a specific UK<->Sackmann pairing (both id columns filled in) -
       skipped entirely by the automatic matcher, so a rerun can't reassign it.
    2. Backfill an `official_tournament_id` the automatic extraction couldn't
       resolve (e.g. the `M0xx`-era rows - see module docstring) by filling in
       just `sackmann_tourney_id` + `official_tournament_id`, leaving the UK
       side to be matched normally.
    """
    manual_matches = (
        manual_matches if manual_matches is not None else pd.DataFrame(columns=MANUAL_MATCH_COLUMNS)
    )
    manual_year = (
        manual_matches.loc[manual_matches["year"] == year]
        if not manual_matches.empty
        else manual_matches
    )

    # UK names are often sponsor names (e.g. "BMW Open") while Sackmann uses the
    # host city (e.g. "Munich"), so the UK "location" is matched against too.
    uk = df_uk_tourneys[
        [
            "uk_tournament_id",
            "source_event_key",
            "tournament_name",
            "location",
            "surface",
            "start_date",
            "end_date",
        ]
    ].copy()
    sack = df_sackman_tourneys[
        ["tourney_id", "tournament_name", "surface", "start_date", "end_date"]
    ].copy()

    uk["start_date"] = pd.to_datetime(uk["start_date"])
    sack["start_date"] = pd.to_datetime(sack["start_date"])

    uk["name_norm"] = uk["tournament_name"].map(normalize_tournament_name)
    uk["location_norm"] = uk["location"].map(normalize_tournament_name)
    sack["name_norm"] = sack["tournament_name"].map(normalize_tournament_name)

    candidates = []
    for uk_row in uk.itertuples():
        for sack_row in sack.itertuples():
            # try the UK sponsor name AND the UK host-city location against the Sackmann name
            sack_name_norm = str(sack_row.name_norm)
            name_score = max(
                SequenceMatcher(None, str(uk_row.name_norm), sack_name_norm).ratio(),
                SequenceMatcher(None, str(uk_row.location_norm), sack_name_norm).ratio(),
            )
            d_score = date_score(uk_row.start_date, sack_row.start_date, max_date_diff_days)
            surface_match = float(uk_row.surface == sack_row.surface)
            score = 0.5 * name_score + 0.4 * d_score + 0.1 * surface_match
            candidates.append(
                {
                    "uk_source_event_key": uk_row.source_event_key,
                    "sackmann_tourney_id": sack_row.tourney_id,
                    "location": uk_row.location,
                    "uk_name": uk_row.tournament_name,
                    "sackmann_name": sack_row.tournament_name,
                    "score": score,
                }
            )

    candidates_df = pd.DataFrame(candidates).sort_values("score", ascending=False)

    # Only a *forced pairing* (both ids given) is pre-seeded so the automatic
    # matcher never touches it - an id-only backfill (see docstring) leaves the
    # pairing to be found normally and is applied as an override afterwards.
    manual_full_pairs = manual_year.loc[
        manual_year["uk_source_event_key"].notna() & manual_year["sackmann_tourney_id"].notna()
    ]
    matched_uk_keys: set = set(manual_full_pairs["uk_source_event_key"])
    matched_sack_ids: set = set(manual_full_pairs["sackmann_tourney_id"])
    matches = []
    for row in candidates_df.to_dict("records"):
        if row["score"] < min_match_score:
            break  # sorted descending, nothing better remains
        uk_key = row["uk_source_event_key"]
        sackmann_id = row["sackmann_tourney_id"]
        if uk_key in matched_uk_keys or sackmann_id in matched_sack_ids:
            continue
        matched_uk_keys.add(row["uk_source_event_key"])
        matched_sack_ids.add(row["sackmann_tourney_id"])
        matches.append(
            {
                "year": year,
                "uk_source_event_key": row["uk_source_event_key"],
                "sackmann_tourney_id": row["sackmann_tourney_id"],
                "score": row["score"],
                "location": row["location"],
                "uk_name": row["uk_name"],
                "sackmann_name": row["sackmann_name"],
            }
        )
    matched_df = pd.DataFrame(matches)

    unmatched_uk = uk.loc[~uk["source_event_key"].isin(matched_uk_keys), "source_event_key"]
    unmatched_sack = sack.loc[~sack["tourney_id"].isin(matched_sack_ids), "tourney_id"]

    unmatched_uk_df = pd.DataFrame(
        {"year": year, "uk_source_event_key": unmatched_uk, "sackmann_tourney_id": pd.NA}
    )
    unmatched_sack_df = pd.DataFrame(
        {"year": year, "uk_source_event_key": pd.NA, "sackmann_tourney_id": unmatched_sack}
    )

    frames = [matched_df, unmatched_uk_df, unmatched_sack_df, manual_full_pairs]
    link_df = pd.concat([f[LINK_COLUMNS] for f in frames if not f.empty], ignore_index=True)
    link_df = link_df.sort_values(
        ["uk_source_event_key", "sackmann_tourney_id"], na_position="last"
    ).reset_index(drop=True)
    link_df["official_tournament_id"] = (
        link_df["sackmann_tourney_id"].map(extract_official_tournament_id).astype("Int64")
    )

    # Manual overrides (forced pairings and id-only backfills alike) win even where
    # the automatic extraction found nothing.
    overrides = manual_year.dropna(subset=["sackmann_tourney_id", "official_tournament_id"])
    if not overrides.empty:
        override_by_sackmann_id = overrides.set_index("sackmann_tourney_id")["official_tournament_id"]
        mask = link_df["sackmann_tourney_id"].isin(override_by_sackmann_id.index)
        link_df.loc[mask, "official_tournament_id"] = (
            link_df.loc[mask, "sackmann_tourney_id"].map(override_by_sackmann_id).astype("Int64")
        )

    review_columns = ["score", "location", "uk_name", "sackmann_name"]
    review_df = (
        matched_df[review_columns].sort_values("score").reset_index(drop=True)
        if not matched_df.empty
        else pd.DataFrame(columns=review_columns)
    )

    return TournamentMatchResult(
        link_df=link_df,
        review_df=review_df,
        uk_total=len(uk),
        sackmann_total=len(sack),
        matched_count=len(matched_df),
        manual_match_count=len(manual_full_pairs),
    )


class LocationCrosswalkResult(NamedTuple):
    """`location_key -> official_tournament_id` crosswalk plus any ambiguous locations found."""

    crosswalk: pd.DataFrame
    ambiguous_locations: set[str]


def build_location_crosswalk(
    link_df: pd.DataFrame, df_uk_tourneys: pd.DataFrame
) -> LocationCrosswalkResult:
    """Build a `location_key -> official_tournament_id` crosswalk from one match run's `link_df`.

    A UK tournament's `location` (host city) is stable across years, so once a
    location has been matched here it never needs fuzzy-matching again - just
    normalize the location and look it up. A location isn't always unique to one
    tournament though (e.g. Paris hosts both Roland Garros and the Paris
    Masters) - detected automatically via a nunique-per-location check, and only
    those ambiguous locations fall back to a composite `location + tournament_name`
    key (every other location keeps the plain, bare-location key).
    """
    uk = df_uk_tourneys.copy()
    uk["location_norm"] = uk["location"].map(normalize_tournament_name)
    uk["name_norm"] = uk["tournament_name"].map(normalize_tournament_name)

    resolved = link_df.dropna(subset=["uk_source_event_key", "official_tournament_id"]).merge(
        uk[["source_event_key", "location", "location_norm", "name_norm"]],
        left_on="uk_source_event_key",
        right_on="source_event_key",
        how="left",
    )

    ids_per_location = resolved.groupby("location_norm")["official_tournament_id"].nunique()
    ambiguous_locations = set(ids_per_location[ids_per_location > 1].index)

    resolved["location_key"] = resolved["location_norm"].where(
        ~resolved["location_norm"].isin(ambiguous_locations),
        resolved["location_norm"] + "|" + resolved["name_norm"],
    )

    crosswalk = (
        resolved[["location_key", "official_tournament_id", "location"]]
        .drop_duplicates(subset="location_key")
        .sort_values("location_key")
        .reset_index(drop=True)
    )

    return LocationCrosswalkResult(crosswalk=crosswalk, ambiguous_locations=ambiguous_locations)


def build_source_links(link_df: pd.DataFrame) -> pd.DataFrame:
    """Long/tidy per-source id table: one row per `(source, year, source_tournament_id)`.

    `official_tournament_id` is the canonical/master id; everything else - a UK
    `source_event_key`, a Sackmann `tourney_id`, or any future source's own id
    scheme - is just one source's way of pointing at that same tournament
    instance for a given year. Onboarding a new source later never needs a
    schema change here, just more rows tagged with that source's name.

    A row is kept even when `official_tournament_id` couldn't be resolved (e.g.
    the `M0xx`-era Sackmann ids - see module docstring) - a confirmed
    UK<->Sackmann match shouldn't be silently discarded just because the third,
    permanent-id leg is temporarily unknown. Backfill it later via `manual_matches`.
    """
    return pd.concat(
        [
            link_df.dropna(subset=["uk_source_event_key"])[
                ["official_tournament_id", "year", "uk_source_event_key"]
            ]
            .rename(columns={"uk_source_event_key": "source_tournament_id"})
            .assign(source="tennis_data_uk"),
            link_df.dropna(subset=["sackmann_tourney_id"])[
                ["official_tournament_id", "year", "sackmann_tourney_id"]
            ]
            .rename(columns={"sackmann_tourney_id": "source_tournament_id"})
            .assign(source="sackmann"),
        ],
        ignore_index=True,
    )[["official_tournament_id", "year", "source", "source_tournament_id"]]


def pivot_source_links(source_links: pd.DataFrame) -> pd.DataFrame:
    """Pivot the long/tidy source-links table into one row per `(official_tournament_id, year)`.

    The persisted `*_tournament_source_links.csv` is long/tidy (one row per
    source), which is great for adding new sources but awkward for the common
    question "what's the Sackmann id for this UK tournament?" (or vice versa).
    This pivots it wide - one column per source, named `<source>_id` - so that
    lookup is a single row filter, without re-running the matching pipeline.

    Example:
        >>> wide = pivot_source_links(pd.read_csv(result.source_links_path))
        >>> wide.loc[wide["tennis_data_uk_id"] == "2024_4_auckland_asb_classic"]
        official_tournament_id  year tennis_data_uk_id  sackmann_id
                            301  2024  2024_4_auckland_asb_classic  2024-0301
    """
    wide = source_links.pivot_table(
        index=["official_tournament_id", "year"],
        columns="source",
        values="source_tournament_id",
        aggfunc="first",
    )
    wide.columns = [f"{source}_id" for source in wide.columns]
    return wide.reset_index()


__all__ = [
    "LINK_COLUMNS",
    "MAX_DATE_DIFF_DAYS",
    "MIN_MATCH_SCORE",
    "LocationCrosswalkResult",
    "TournamentMatchResult",
    "build_location_crosswalk",
    "build_source_links",
    "date_score",
    "extract_official_tournament_id",
    "match_uk_to_sackmann_tourneys",
    "normalize_tournament_name",
    "pivot_source_links",
]
