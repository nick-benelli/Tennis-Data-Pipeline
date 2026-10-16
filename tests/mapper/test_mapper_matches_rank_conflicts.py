"""Regression for Wimbledon 2014's swapped Halep-Bencic / Halep-Diyas links.

Reduced UK rows: data/clean/uk/wta/uk_wta_singles_clean_2014.csv, lines 1503/1512
at 52c96435d038658c5361a35f09d8147d02d7ce59. Canonical rows: wta/wta_matches_2014.csv,
lines 2618/2632 in Aneeshers/tennis-sackmann-archive at
83733587353df8a41f2fd4f516147d5aa83f5a8d. No downloads are needed by these tests.
"""

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.matches import (
    build_enriched_matches,
    build_manual_rank_and_name_links,
    build_rank_and_name_links,
    build_rank_links,
    player_name_compatible,
)

EVENT = "2014_32_london_wimbledon"
TOURNEY = "2014-W-SL-GBR-01A-2014"
BENCIC_KEY = EVENT + "_2014-06-28_R32_halep_s_bencic_b"
DIYAS_KEY = EVENT + "_2014-07-01_R16_halep_s_diyas_z"


def real_inputs():
    mapper = pd.DataFrame(
        [
            {
                "official_tournament_id": 904,
                "year": 2014,
                "source": "tennis_data_uk",
                "source_tournament_id": EVENT,
            },
            {
                "official_tournament_id": 904,
                "year": 2014,
                "source": "sackmann",
                "source_tournament_id": TOURNEY,
            },
        ]
    )
    uk = pd.DataFrame(
        [
            {
                "source": "tennis_data_uk",
                "tour": "wta",
                "year": 2014,
                "source_event_key": EVENT,
                "source_match_key": BENCIC_KEY,
                "match_date": "2014-06-28",
                "round": "R32",
                "winner_name": "Halep S.",
                "loser_name": "Bencic B.",
                "winner_rank": 3,
                "loser_rank": 72,
                "winner_rank_points": 6280,
                "loser_rank_points": 773,
            },
            {
                "source": "tennis_data_uk",
                "tour": "wta",
                "year": 2014,
                "source_event_key": EVENT,
                "source_match_key": DIYAS_KEY,
                "match_date": "2014-07-01",
                "round": "R16",
                "winner_name": "Halep S.",
                "loser_name": "Diyas Z.",
                "winner_rank": 3,
                "loser_rank": 71,
                "winner_rank_points": 6280,
                "loser_rank_points": 781,
            },
        ]
    )
    sk = pd.DataFrame(
        [
            {
                "tour": "wta",
                "source_year": 2014,
                "tourney_id": TOURNEY,
                "tourney_name": "Wimbledon",
                "tourney_date": "2014-06-23",
                "match_num": 101,
                "round": "R32",
                "score": "6-4 6-1",
                "winner_id": 201594,
                "loser_id": 202505,
                "winner_name": "Simona Halep",
                "loser_name": "Belinda Bencic",
                "winner_rank": 3,
                "loser_rank": 71,
                "winner_rank_points": 6105,
                "loser_rank_points": 797,
            },
            {
                "tour": "wta",
                "source_year": 2014,
                "tourney_id": TOURNEY,
                "tourney_name": "Wimbledon",
                "tourney_date": "2014-06-23",
                "match_num": 115,
                "round": "R16",
                "score": "6-3 6-0",
                "winner_id": 201594,
                "loser_id": 201610,
                "winner_name": "Simona Halep",
                "loser_name": "Zarina Diyas",
                "winner_rank": 3,
                "loser_rank": 72,
                "winner_rank_points": 6105,
                "loser_rank_points": 781,
            },
        ]
    )
    return uk, sk, mapper


def test_wimbledon_2014_rank_conflicts_remain_available_for_pass2():
    uk, sk, mapper = real_inputs()
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert accepted.empty
    assert ambiguous.empty
    assert set(unmatched["source_match_key"]) == {BENCIC_KEY, DIYAS_KEY}


def test_wimbledon_2014_links_correct_opponents_and_enriches_correct_ids():
    uk, sk, mapper = real_inputs()
    accepted, ambiguous, unmatched = build_rank_and_name_links(uk, sk, mapper)
    actual = accepted.set_index("source_match_key")["canonical_match_key"].to_dict()
    assert actual == {
        BENCIC_KEY: TOURNEY + "_101",
        DIYAS_KEY: TOURNEY + "_115",
    }
    assert ambiguous.empty
    assert unmatched.empty
    assert accepted["match_method"].eq("tournament_round_name_pair").all()
    assert accepted["data_quality_flag"].eq("rank_mismatch").all()
    assert not accepted["review_flag"].any()

    enriched = build_enriched_matches(uk, sk, accepted).set_index("source_match_key")
    assert len(enriched) == len(uk)
    assert enriched.loc[BENCIC_KEY, "canonical_loser_id"] == 202505
    assert enriched.loc[DIYAS_KEY, "canonical_loser_id"] == 201610
    assert enriched.loc[BENCIC_KEY, "canonical_loser_name"] == "Belinda Bencic"
    assert enriched.loc[DIYAS_KEY, "canonical_loser_name"] == "Zarina Diyas"


def compatible_inputs():
    uk, sk, mapper = real_inputs()
    uk, sk = uk.iloc[:1].copy(), sk.iloc[:1].copy()
    uk["loser_rank"] = sk["loser_rank"].iloc[0]
    return uk, sk, mapper


@pytest.mark.parametrize(
    ("source", "canonical"),
    [
        ("Bencic B.", "Belinda Bencic"),
        ("Bénčić B.", "Belinda Bencic"),
        ("Auger-Aliassime F.", "Felix Auger Aliassime"),
        ("Wolf J.J.", "J J Wolf"),
        ("Varillas J. P.", "Juan Pablo Varillas"),
    ],
)
def test_compatible_name_variations_survive_conflicting_rounds(source, canonical):
    uk, sk, mapper = compatible_inputs()
    uk["loser_name"] = source
    sk["loser_name"] = canonical
    uk["round"], sk["round"] = "F", "SF"
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert len(accepted) == 1
    assert not accepted.iloc[0]["round_agrees"]
    assert ambiguous.empty and unmatched.empty


@pytest.mark.parametrize(
    ("source", "canonical"),
    [
        ("Ramos-Vinolas A.", "Albert Ramos"),
        ("Fernandez L.A.", "Leylah Fernandez"),
        ("Tsonga J.W.", "Jo-Wilfried Tsonga"),
    ],
)
def test_rank_links_preserve_name_variations_not_recognised_by_name_helper(source, canonical):
    uk, sk, mapper = compatible_inputs()
    uk["loser_name"] = source
    sk["loser_name"] = canonical
    assert not player_name_compatible(source, canonical)
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert len(accepted) == 1
    assert ambiguous.empty and unmatched.empty


@pytest.mark.parametrize("side", ["winner", "loser"])
def test_known_name_and_round_conflicts_remain_unmatched_without_recovery(side):
    uk, sk, mapper = compatible_inputs()
    sk[f"{side}_name"] = "Unrelated Player"
    sk["round"] = "R16"
    for api in (build_rank_links, build_rank_and_name_links):
        accepted, ambiguous, unmatched = api(uk, sk, mapper)
        assert accepted.empty and ambiguous.empty
        assert unmatched.source_match_key.tolist() == [BENCIC_KEY]


@pytest.mark.parametrize("missing", [None, pd.NA, float("nan")])
@pytest.mark.parametrize("frame", ["uk", "sk"])
def test_missing_round_does_not_count_as_conflicting_round(missing, frame):
    uk, sk, mapper = compatible_inputs()
    sk["loser_name"] = "Unrelated Player"
    (uk if frame == "uk" else sk)["round"] = missing
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert len(accepted) == 1
    assert ambiguous.empty and unmatched.empty


@pytest.mark.parametrize("missing", [None, pd.NA, "", "  "])
@pytest.mark.parametrize("frame", ["uk", "sk"])
def test_missing_name_does_not_count_as_conflicting_identity(missing, frame):
    uk, sk, mapper = compatible_inputs()
    sk["round"] = "R16"
    (uk if frame == "uk" else sk)["loser_name"] = missing
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert len(accepted) == 1
    assert ambiguous.empty and unmatched.empty


def test_conflict_filter_does_not_promote_ambiguous_rank_candidates():
    uk, sk, mapper = compatible_inputs()
    conflict = sk.copy()
    conflict["match_num"] = 999
    conflict["round"] = "R16"
    conflict["loser_name"] = "Unrelated Player"
    sk = pd.concat([sk, conflict], ignore_index=True)
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert accepted.empty and unmatched.empty
    assert len(ambiguous) == 2
    assert ambiguous.source_candidate_count.eq(2).all()
    assert ambiguous.canonical_candidate_count.eq(1).all()
    recovered, _, unmatched = build_rank_and_name_links(uk, sk, mapper)
    assert recovered.canonical_match_key.tolist() == [TOURNEY + "_101"]
    assert unmatched.empty


def test_manual_override_precedes_the_name_and_round_guard():
    uk, sk, mapper = real_inputs()
    manual = pd.DataFrame(
        [
            {"year": 2014, "source_match_key": BENCIC_KEY, "canonical_match_key": TOURNEY + "_115"},
        ]
    )
    accepted, _, unmatched = build_manual_rank_and_name_links(uk, sk, mapper, manual)
    # An explicit override remains authoritative even when automatic evidence conflicts.
    assert accepted.source_match_key.tolist() == [BENCIC_KEY]
    assert accepted.canonical_match_key.tolist() == [TOURNEY + "_115"]
    assert accepted.match_method.tolist() == ["manual_override"]
    assert unmatched.source_match_key.tolist() == [DIYAS_KEY]


@pytest.mark.parametrize(("empty_uk", "empty_sk"), [(True, False), (False, True), (True, True)])
def test_rank_guard_handles_empty_candidate_pools(empty_uk, empty_sk):
    uk, sk, mapper = compatible_inputs()
    if empty_uk:
        uk = uk.iloc[:0]
    if empty_sk:
        sk = sk.iloc[:0]
    accepted, ambiguous, unmatched = build_rank_links(uk, sk, mapper)
    assert accepted.empty and ambiguous.empty
    assert len(unmatched) == len(uk)


def test_missing_rank_is_still_recovered_by_pass2():
    uk, sk, mapper = compatible_inputs()
    uk["winner_rank"] = None
    accepted, ambiguous, unmatched = build_rank_and_name_links(uk, sk, mapper)
    assert accepted.canonical_match_key.tolist() == [TOURNEY + "_101"]
    assert accepted.match_method.tolist() == ["tournament_round_name_pair"]
    assert accepted.data_quality_flag.tolist() == ["missing_rank"]
    assert ambiguous.empty and unmatched.empty
