"""Tests for cross-source tournament id matching/crosswalk logic (`mapper.tournaments`)."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.tournaments import (
    backfill_official_ids_from_wta_api,
    build_location_crosswalk,
    build_source_links,
    date_score,
    extract_official_tournament_id,
    match_sackmann_to_wta_api_tourneys,
    match_uk_to_sackmann_tourneys,
    normalize_tournament_name,
    pivot_source_links,
)


def _uk_row(**overrides: object) -> dict:
    row = {
        "uk_tournament_id": 1,
        "source_event_key": "2025_1_montpellier_open_sud_de_france",
        "tournament_name": "Open Sud de France",
        "location": "Montpellier",
        "surface": "hard",
        "start_date": "2025-01-27",
        "end_date": "2025-02-02",
    }
    row.update(overrides)
    return row


def _sack_row(**overrides: object) -> dict:
    row = {
        "tourney_id": "2025-0375",
        "tournament_name": "Montpellier",
        "surface": "hard",
        "start_date": "2025-01-27",
        "end_date": "2025-02-02",
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Queen's Club", "queen s club"),
        ("  Sao Paulo  ", "sao paulo"),
        ("Roland Garros!", "roland garros"),
    ],
)
def test_normalize_tournament_name(raw: str, expected: str) -> None:
    assert normalize_tournament_name(raw) == expected


def test_date_score_decreases_with_distance() -> None:
    """Same day scores 1.0; max_days apart (or further) scores 0.0."""
    same_day = pd.Timestamp("2025-01-01")
    assert date_score(same_day, same_day) == 1.0
    assert date_score(same_day, same_day + pd.Timedelta(days=10)) == 0.0
    assert date_score(same_day, same_day + pd.Timedelta(days=20)) == 0.0


@pytest.mark.parametrize(
    "sackmann_tourney_id,expected",
    [
        ("2025-0375", 375),
        ("2025-9900", 9900),
        (pd.NA, pd.NA),
        ("2016-M001", pd.NA),  # M0xx-era non-permanent id, see module docstring
        ("2016-O16", pd.NA),  # Olympics code, not a real official tournament id
    ],
)
def test_extract_official_tournament_id(sackmann_tourney_id: object, expected: object) -> None:
    result = extract_official_tournament_id(sackmann_tourney_id)
    if pd.isna(expected):
        assert pd.isna(result)
    else:
        assert result == expected


def test_match_uk_to_sackmann_tourneys_matches_exact_pair() -> None:
    """A single unambiguous UK/Sackmann pair matches with a perfect score."""
    df_uk = pd.DataFrame([_uk_row()])
    df_sack = pd.DataFrame([_sack_row()])

    result = match_uk_to_sackmann_tourneys(df_uk, df_sack, 2025)

    assert result.uk_total == 1
    assert result.sackmann_total == 1
    assert result.matched_count == 1
    assert len(result.link_df) == 1
    row = result.link_df.iloc[0]
    assert row["uk_source_event_key"] == "2025_1_montpellier_open_sud_de_france"
    assert row["sackmann_tourney_id"] == "2025-0375"
    assert row["official_tournament_id"] == 375
    assert result.review_df.iloc[0]["score"] == pytest.approx(1.0)


def test_match_uk_to_sackmann_tourneys_leaves_unmatched_blank() -> None:
    """An unmatched UK/Sackmann tournament is kept with a blank id on the other side."""
    df_uk = pd.DataFrame([_uk_row()])
    df_sack = pd.DataFrame(
        [_sack_row(tourney_id="2025-7696", tournament_name="Next Gen Finals", start_date="2025-12-17")]
    )

    result = match_uk_to_sackmann_tourneys(df_uk, df_sack, 2025)

    assert result.matched_count == 0
    assert len(result.link_df) == 2
    assert result.link_df["uk_source_event_key"].isna().sum() == 1
    assert result.link_df["sackmann_tourney_id"].isna().sum() == 1


def test_manual_matches_are_excluded_from_automatic_matching() -> None:
    """A forced pairing is used as-is and never reconsidered by the fuzzy matcher."""
    df_uk = pd.DataFrame([_uk_row()])
    df_sack = pd.DataFrame([_sack_row()])
    manual_matches = pd.DataFrame(
        {
            "year": [2025],
            "uk_source_event_key": ["2025_1_montpellier_open_sud_de_france"],
            "sackmann_tourney_id": ["2025-0375"],
            "official_tournament_id": pd.array([375], dtype="Int64"),
        }
    )

    result = match_uk_to_sackmann_tourneys(df_uk, df_sack, 2025, manual_matches=manual_matches)

    assert result.manual_match_count == 1
    assert result.matched_count == 0  # the pair never entered the automatic matcher
    assert len(result.link_df) == 1
    assert result.link_df.iloc[0]["official_tournament_id"] == 375


def test_manual_matches_backfill_unresolved_official_id() -> None:
    """A manual override can fill in an official_tournament_id the automatic extraction
    couldn't resolve (e.g. an M0xx-era Sackmann id), without forcing the UK<->Sackmann
    pairing itself."""
    df_uk = pd.DataFrame([_uk_row()])
    df_sack = pd.DataFrame([_sack_row(tourney_id="2016-M006")])
    manual_matches = pd.DataFrame(
        {
            "year": [2016],
            "uk_source_event_key": [pd.NA],
            "sackmann_tourney_id": ["2016-M006"],
            "official_tournament_id": pd.array([404], dtype="Int64"),
        }
    )

    result = match_uk_to_sackmann_tourneys(df_uk, df_sack, 2016, manual_matches=manual_matches)

    assert result.matched_count == 1  # UK<->Sackmann pairing still found automatically
    row = result.link_df.loc[result.link_df["sackmann_tourney_id"] == "2016-M006"].iloc[0]
    assert row["official_tournament_id"] == 404


def test_manual_matches_backfill_uk_only_when_no_sackmann_counterpart() -> None:
    """A manual override can document an official_tournament_id for a UK tournament that has
    no Sackmann counterpart at all, keyed on uk_source_event_key alone."""
    df_uk = pd.DataFrame([_uk_row(source_event_key="2007_2_gold_coast", tournament_name="Gold Coast")])
    df_sack = pd.DataFrame(
        [
            _sack_row(
                tourney_id="2007-W-XXX-01A-2007",
                tournament_name="Unrelated Event",
                surface="clay",
                start_date="2007-06-15",
                end_date="2007-06-15",
            )
        ]
    )
    manual_matches = pd.DataFrame(
        {
            "year": [2025],
            "uk_source_event_key": ["2007_2_gold_coast"],
            "sackmann_tourney_id": [pd.NA],
            "official_tournament_id": pd.array([1066], dtype="Int64"),
        }
    )

    result = match_uk_to_sackmann_tourneys(df_uk, df_sack, 2025, manual_matches=manual_matches)

    row = result.link_df.loc[result.link_df["uk_source_event_key"] == "2007_2_gold_coast"].iloc[0]
    assert row["official_tournament_id"] == 1066
    assert pd.isna(row["sackmann_tourney_id"])  # no Sackmann counterpart, left blank


def test_build_location_crosswalk_disambiguates_shared_location() -> None:
    """A location hosting two distinct tournaments (e.g. Paris) falls back to a composite key."""
    df_uk = pd.DataFrame(
        [
            _uk_row(
                uk_tournament_id=1,
                source_event_key="2025_1_paris_french_open",
                tournament_name="French Open",
                location="Paris",
            ),
            _uk_row(
                uk_tournament_id=2,
                source_event_key="2025_2_paris_bnp_paribas_masters",
                tournament_name="BNP Paribas Masters",
                location="Paris",
            ),
        ]
    )
    link_df = pd.DataFrame(
        {
            "year": [2025, 2025],
            "uk_source_event_key": ["2025_1_paris_french_open", "2025_2_paris_bnp_paribas_masters"],
            "sackmann_tourney_id": ["2025-0520", "2025-0352"],
            "official_tournament_id": [520, 352],
        }
    )

    result = build_location_crosswalk(link_df, df_uk)

    assert result.ambiguous_locations == {"paris"}
    assert set(result.crosswalk["location_key"]) == {"paris|french open", "paris|bnp paribas masters"}


def test_build_location_crosswalk_keeps_bare_key_when_unambiguous() -> None:
    df_uk = pd.DataFrame([_uk_row()])
    link_df = pd.DataFrame(
        {
            "year": [2025],
            "uk_source_event_key": ["2025_1_montpellier_open_sud_de_france"],
            "sackmann_tourney_id": ["2025-0375"],
            "official_tournament_id": [375],
        }
    )

    result = build_location_crosswalk(link_df, df_uk)

    assert result.ambiguous_locations == set()
    assert result.crosswalk["location_key"].tolist() == ["montpellier"]
    assert result.crosswalk["official_tournament_id"].tolist() == [375]


def test_build_source_links_produces_long_format_rows() -> None:
    link_df = pd.DataFrame(
        {
            "year": [2025],
            "uk_source_event_key": ["2025_1_montpellier_open_sud_de_france"],
            "sackmann_tourney_id": ["2025-0375"],
            "official_tournament_id": [375],
        }
    )

    source_links = build_source_links(link_df)

    assert set(source_links["source"]) == {"tennis_data_uk", "sackmann"}
    assert len(source_links) == 2
    assert set(source_links["official_tournament_id"]) == {375}


def test_build_source_links_keeps_rows_with_unresolved_official_id() -> None:
    """A confirmed UK<->Sackmann match isn't discarded just because the id (e.g. an
    M0xx-era Sackmann code) couldn't be resolved - see extract_official_tournament_id."""
    link_df = pd.DataFrame(
        {
            "year": [2016],
            "uk_source_event_key": ["2016_19_indian_wells_bnp_paribas_open"],
            "sackmann_tourney_id": ["2016-M006"],
            "official_tournament_id": pd.array([pd.NA], dtype="Int64"),
        }
    )

    source_links = build_source_links(link_df)

    assert len(source_links) == 2
    assert source_links["official_tournament_id"].isna().all()
    assert set(source_links["source_tournament_id"]) == {
        "2016_19_indian_wells_bnp_paribas_open",
        "2016-M006",
    }


def test_pivot_source_links_joins_uk_and_sackmann_ids_side_by_side() -> None:
    """The long/tidy source-links table pivots into one row per tournament instance."""
    source_links = pd.DataFrame(
        {
            "official_tournament_id": [301, 301],
            "year": [2024, 2024],
            "source": ["sackmann", "tennis_data_uk"],
            "source_tournament_id": ["2024-0301", "2024_4_auckland_asb_classic"],
        }
    )

    wide = pivot_source_links(source_links)

    assert len(wide) == 1
    row = wide.iloc[0]
    assert row["official_tournament_id"] == 301
    assert row["year"] == 2024
    assert row["sackmann_id"] == "2024-0301"
    assert row["tennis_data_uk_id"] == "2024_4_auckland_asb_classic"


def _wta_api_row(**overrides: object) -> dict:
    row = {
        "official_tournament_id": 303,
        "group_name": "PATTAYA CITY",
        "title": "PTT PATTAYA WOMEN'S OPEN - PATTAYA CITY, THAILAND",
        "surface": "Hard",
        "start_date": "2010-02-08",
    }
    row.update(overrides)
    return row


def test_match_sackmann_to_wta_api_tourneys_matches_pre_2016_non_numeric_id() -> None:
    """Sackmann's pre-2016 WTA tourney_id ("2010-W-INT-THA-01A-2010") can't be parsed for an
    official id, but the WTA-API's own permanent id can still be recovered by name/date match."""
    df_sack = pd.DataFrame(
        [
            _sack_row(
                tourney_id="2010-W-INT-THA-01A-2010",
                tournament_name="Pattaya",
                start_date="2010-02-08",
                end_date="2010-02-08",
            )
        ]
    )
    df_wta_api = pd.DataFrame([_wta_api_row()])

    result = match_sackmann_to_wta_api_tourneys(df_sack, df_wta_api)

    assert result.sackmann_total == 1
    assert result.wta_api_total == 1
    assert result.matched_count == 1
    row = result.link_df.iloc[0]
    assert row["sackmann_tourney_id"] == "2010-W-INT-THA-01A-2010"
    assert row["official_tournament_id"] == 303


def test_match_sackmann_to_wta_api_tourneys_no_match_below_threshold() -> None:
    df_sack = pd.DataFrame(
        [
            _sack_row(
                tourney_id="2010-W-INT-XXX-01A-2010",
                tournament_name="Nowhere",
                start_date="2010-09-01",
                end_date="2010-09-01",
            )
        ]
    )
    df_wta_api = pd.DataFrame([_wta_api_row()])

    result = match_sackmann_to_wta_api_tourneys(df_sack, df_wta_api)

    assert result.matched_count == 0
    assert result.link_df.empty


def test_backfill_official_ids_from_wta_api_fills_only_blank_ids() -> None:
    link_df = pd.DataFrame(
        {
            "year": [2010, 2010],
            "uk_source_event_key": ["2010_1_pattaya_thailand_open", "2010_2_other"],
            "sackmann_tourney_id": ["2010-W-INT-THA-01A-2010", "2010-9999"],
            "official_tournament_id": pd.array([pd.NA, 999], dtype="Int64"),
        }
    )
    sackmann_to_wta_api = pd.DataFrame(
        {
            "sackmann_tourney_id": ["2010-W-INT-THA-01A-2010"],
            "official_tournament_id": pd.array([303], dtype="Int64"),
        }
    )

    result = backfill_official_ids_from_wta_api(link_df, sackmann_to_wta_api)

    backfilled = result.loc[result["sackmann_tourney_id"] == "2010-W-INT-THA-01A-2010"].iloc[0]
    already_resolved = result.loc[result["sackmann_tourney_id"] == "2010-9999"].iloc[0]
    assert backfilled["official_tournament_id"] == 303
    assert already_resolved["official_tournament_id"] == 999  # never overwritten


def test_backfill_official_ids_from_wta_api_noop_when_no_wta_api_matches() -> None:
    link_df = pd.DataFrame(
        {
            "year": [2010],
            "uk_source_event_key": ["2010_1_pattaya_thailand_open"],
            "sackmann_tourney_id": ["2010-W-INT-THA-01A-2010"],
            "official_tournament_id": pd.array([pd.NA], dtype="Int64"),
        }
    )

    result = backfill_official_ids_from_wta_api(link_df, pd.DataFrame())

    assert result["official_tournament_id"].isna().all()
