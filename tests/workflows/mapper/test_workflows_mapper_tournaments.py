"""Tests for the cross-source tournament mapping workflow (`workflows.mapper.tournaments`)."""

from __future__ import annotations

import logging

import pandas as pd

from tennis_data_pipeline.workflows.mapper.tournaments import (
    _manual_force_keys,
    _merge_source_links,
    _warn_on_crosswalk_conflicts,
)


def _row(**overrides: object) -> dict:
    row = {
        "official_tournament_id": pd.NA,
        "year": 2016,
        "source": "sackmann",
        "source_tournament_id": "2016-M006",
    }
    row.update(overrides)
    return row


def test_merge_source_links_backfills_a_previously_unresolved_id() -> None:
    """A freshly computed non-blank id replaces an existing blank one for the same key."""
    existing = pd.DataFrame([_row(official_tournament_id=pd.NA)]).astype(
        {"official_tournament_id": "Int64"}
    )
    new = pd.DataFrame([_row(official_tournament_id=404)]).astype({"official_tournament_id": "Int64"})

    merged = _merge_source_links(existing, new, ["source", "year", "source_tournament_id"])

    assert len(merged) == 1
    assert merged.iloc[0]["official_tournament_id"] == 404


def test_merge_source_links_keeps_existing_resolved_id_over_a_new_one() -> None:
    """An existing filled-in id is never overwritten by a freshly computed one (hand corrections)."""
    existing = pd.DataFrame([_row(official_tournament_id=404)]).astype(
        {"official_tournament_id": "Int64"}
    )
    new = pd.DataFrame([_row(official_tournament_id=999)]).astype({"official_tournament_id": "Int64"})

    merged = _merge_source_links(existing, new, ["source", "year", "source_tournament_id"])

    assert len(merged) == 1
    assert merged.iloc[0]["official_tournament_id"] == 404


def test_merge_source_links_keeps_unrelated_rows_from_both_sides() -> None:
    existing = pd.DataFrame([_row(source_tournament_id="2016-M006")]).astype(
        {"official_tournament_id": "Int64"}
    )
    new = pd.DataFrame([_row(source_tournament_id="2016-M007", official_tournament_id=403)]).astype(
        {"official_tournament_id": "Int64"}
    )

    merged = _merge_source_links(existing, new, ["source", "year", "source_tournament_id"])

    assert len(merged) == 2
    assert set(merged["source_tournament_id"]) == {"2016-M006", "2016-M007"}


def test_merge_source_links_force_key_overrides_a_wrong_existing_non_blank_id() -> None:
    """Regression test for the 2022 WTA Melbourne Summer Set 1/2 swap.

    Without `force_keys`, a stale-but-non-blank existing id (from an earlier
    buggy automatic match) can never be corrected by adding a `manual_matches`
    override and rerunning - `force_keys` lets that specific key's freshly
    computed value win regardless.
    """
    existing = pd.DataFrame([_row(official_tournament_id=2059)]).astype(
        {"official_tournament_id": "Int64"}
    )
    new = pd.DataFrame([_row(official_tournament_id=2058)]).astype({"official_tournament_id": "Int64"})

    merged = _merge_source_links(
        existing,
        new,
        ["source", "year", "source_tournament_id"],
        force_keys={("sackmann", 2016, "2016-M006")},
    )

    assert len(merged) == 1
    assert merged.iloc[0]["official_tournament_id"] == 2058


def test_merge_source_links_non_forced_key_still_keeps_existing_id() -> None:
    """A key not covered by `force_keys` keeps the existing-wins behavior unchanged."""
    existing = pd.DataFrame([_row(official_tournament_id=404)]).astype(
        {"official_tournament_id": "Int64"}
    )
    new = pd.DataFrame([_row(official_tournament_id=999)]).astype({"official_tournament_id": "Int64"})

    merged = _merge_source_links(
        existing,
        new,
        ["source", "year", "source_tournament_id"],
        force_keys={("sackmann", 2016, "some-other-id")},
    )

    assert merged.iloc[0]["official_tournament_id"] == 404


def test_manual_force_keys_covers_all_three_override_kinds() -> None:
    manual_year = pd.DataFrame(
        [
            {  # forced pairing
                "year": 2022,
                "uk_source_event_key": "2022_2_melbourne_melbourne_summer_set_1",
                "sackmann_tourney_id": "2022-2058",
                "official_tournament_id": pd.NA,
            },
            {  # sackmann-id-only backfill
                "year": 2016,
                "uk_source_event_key": pd.NA,
                "sackmann_tourney_id": "2016-M006",
                "official_tournament_id": 609,
            },
            {  # UK-only backfill
                "year": 2007,
                "uk_source_event_key": "2007_2_gold_coast_mondial",
                "sackmann_tourney_id": pd.NA,
                "official_tournament_id": 1066,
            },
        ]
    )

    keys = _manual_force_keys(manual_year)

    assert keys == {
        ("tennis_data_uk", 2022, "2022_2_melbourne_melbourne_summer_set_1"),
        ("sackmann", 2022, "2022-2058"),
        ("sackmann", 2016, "2016-M006"),
        ("tennis_data_uk", 2007, "2007_2_gold_coast_mondial"),
    }


def test_manual_force_keys_empty_for_no_manual_matches_this_year() -> None:
    assert _manual_force_keys(pd.DataFrame()) == set()


def _crosswalk_row(**overrides: object) -> dict:
    row = {"location_key": "singapore", "official_tournament_id": 1096, "location": "Singapore"}
    row.update(overrides)
    return row


def test_warn_on_crosswalk_conflicts_logs_for_bare_key_id_mismatch(caplog) -> None:
    """A bare location_key resolving to a different id than what's persisted logs a warning."""
    existing = pd.DataFrame([_crosswalk_row(official_tournament_id=808)])
    new = pd.DataFrame([_crosswalk_row(official_tournament_id=1096)])

    with caplog.at_level(logging.WARNING):
        _warn_on_crosswalk_conflicts(existing, new)

    assert any("singapore" in record.message for record in caplog.records)


def test_warn_on_crosswalk_conflicts_ignores_composite_keys(caplog) -> None:
    """A composite location|name key is exempt - it's meant to hold distinct ids on purpose."""
    existing = pd.DataFrame(
        [_crosswalk_row(location_key="singapore|wta finals", official_tournament_id=808)]
    )
    new = pd.DataFrame(
        [_crosswalk_row(location_key="singapore|wta finals", official_tournament_id=1096)]
    )

    with caplog.at_level(logging.WARNING):
        _warn_on_crosswalk_conflicts(existing, new)

    assert not caplog.records


def test_warn_on_crosswalk_conflicts_ignores_already_known_ambiguous_location(caplog) -> None:
    """A bare-key conflict is silent once the location already has a composite key on file."""
    existing = pd.DataFrame(
        [
            _crosswalk_row(location_key="singapore", official_tournament_id=808),
            _crosswalk_row(location_key="singapore|singapore open", official_tournament_id=1096),
        ]
    )
    new = pd.DataFrame([_crosswalk_row(location_key="singapore", official_tournament_id=1096)])

    with caplog.at_level(logging.WARNING):
        _warn_on_crosswalk_conflicts(existing, new)

    assert not caplog.records


def test_warn_on_crosswalk_conflicts_silent_when_ids_match(caplog) -> None:
    """No warning when the fresh row agrees with what's already persisted."""
    existing = pd.DataFrame([_crosswalk_row(official_tournament_id=1096)])
    new = pd.DataFrame([_crosswalk_row(official_tournament_id=1096)])

    with caplog.at_level(logging.WARNING):
        _warn_on_crosswalk_conflicts(existing, new)

    assert not caplog.records
