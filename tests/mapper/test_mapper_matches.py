"""Tests for match-level linking logic (`mapper.matches`): Pass 1 and Pass 2."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.mapper.matches import (
    MATCH_METHOD_TOURNAMENT_RANK_UNIQUE,
    MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR,
    add_sackmann_match_key,
    attach_tournament_ids,
    build_name_pair_links,
    build_rank_and_name_links,
    build_rank_links,
    classify_rank_candidates,
    generate_name_pair_candidates,
    generate_rank_candidates,
    normalize_name,
    parse_tennis_data_name,
    player_name_compatible,
)


def _tournament_mapper() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "official_tournament_id": 520,
                "year": 2025,
                "source": "tennis_data_uk",
                "source_tournament_id": "2025_29_paris_french_open",
            },
            {
                "official_tournament_id": 520,
                "year": 2025,
                "source": "sackmann",
                "source_tournament_id": "2025-520",
            },
            {
                "official_tournament_id": 999,
                "year": 2025,
                "source": "tennis_data_uk",
                "source_tournament_id": "2025_1_other_event",
            },
            {
                "official_tournament_id": 999,
                "year": 2025,
                "source": "sackmann",
                "source_tournament_id": "2025-999",
            },
        ]
    )


def _uk_row(**overrides: object) -> dict:
    row: dict = {
        "source": "tennis_data_uk",
        "tour": "atp",
        "year": 2025,
        "source_event_key": "2025_29_paris_french_open",
        "tournament_name": "French Open",
        "match_date": "2025-06-01",
        "winner_name": "Fritz T.",
        "loser_name": "Nava E.",
        "winner_rank": 1,
        "loser_rank": 5,
        "winner_rank_points": 10000,
        "loser_rank_points": 3000,
        "round": "F",
        "source_match_key": "uk_1",
    }
    row.update(overrides)
    return row


def _sk_row(**overrides: object) -> dict:
    row: dict = {
        "tourney_id": "2025-520",
        "tourney_name": "Roland Garros",
        "surface": "clay",
        "tourney_level": "G",
        "tourney_date": "2025-05-25",
        "match_num": 300,
        "winner_id": 111,
        "loser_id": 222,
        "winner_name": "Taylor Fritz",
        "loser_name": "Emilio Nava",
        "winner_rank": 1,
        "loser_rank": 5,
        "winner_rank_points": 10000,
        "loser_rank_points": 3000,
        "round": "F",
        "source_year": 2025,
        "tour": "atp",
    }
    row.update(overrides)
    return row


def test_attach_tournament_ids_maps_official_id() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    result = attach_tournament_ids(
        uk_df,
        _tournament_mapper(),
        source="tennis_data_uk",
        match_tournament_col="source_event_key",
        year_col="year",
    )

    assert result["official_tournament_id"].tolist() == [520]
    # original columns untouched, only the new column was added
    assert set(uk_df.columns) <= set(result.columns)


def test_add_sackmann_match_key() -> None:
    sackmann_df = pd.DataFrame([_sk_row(tourney_id="2025-520", match_num=300)])
    result = add_sackmann_match_key(sackmann_df)
    assert result["canonical_match_key"].tolist() == ["2025-520_300"]


def test_build_rank_links_accepts_unique_rank_pair() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert len(accepted) == 1
    assert accepted.iloc[0]["source_match_key"] == "uk_1"
    assert accepted.iloc[0]["canonical_match_key"] == "2025-520_300"
    assert accepted.iloc[0]["match_method"] == MATCH_METHOD_TOURNAMENT_RANK_UNIQUE
    assert not accepted.iloc[0]["review_flag"]
    assert accepted.iloc[0]["winner_id"] == 111
    assert accepted.iloc[0]["loser_id"] == 222
    assert accepted.iloc[0]["round_agrees"]
    assert accepted.iloc[0]["winner_rank_points_diff"] == 0
    assert accepted.iloc[0]["loser_rank_points_diff"] == 0
    assert ambiguous.empty
    assert unmatched.empty


def test_build_rank_links_flags_ambiguous_source_match() -> None:
    """Two Sackmann rows share the same rank pair -> the uk row can't be resolved."""
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame(
        [
            _sk_row(match_num=300),
            _sk_row(match_num=301),
        ]
    )

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert unmatched.empty
    assert set(ambiguous["canonical_match_key"]) == {"2025-520_300", "2025-520_301"}
    assert (ambiguous["source_candidate_count"] == 2).all()
    assert (ambiguous["canonical_candidate_count"] == 1).all()


def test_build_rank_links_flags_ambiguous_canonical_match() -> None:
    """Two uk rows share the same rank pair -> the sackmann row can't be resolved."""
    uk_df = pd.DataFrame(
        [
            _uk_row(source_match_key="uk_1"),
            _uk_row(source_match_key="uk_2"),
        ]
    )
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert unmatched.empty
    assert set(ambiguous["source_match_key"]) == {"uk_1", "uk_2"}
    assert (ambiguous["canonical_candidate_count"] == 2).all()
    assert (ambiguous["source_candidate_count"] == 1).all()


def test_build_rank_links_treats_missing_tournament_mapping_as_unmatched() -> None:
    uk_df = pd.DataFrame([_uk_row(source_event_key="unmapped_event")])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]
    assert pd.isna(unmatched.iloc[0]["official_tournament_id"])


def test_build_rank_links_treats_missing_rank_as_unmatched() -> None:
    uk_df = pd.DataFrame([_uk_row(winner_rank=None)])
    sackmann_df = pd.DataFrame([_sk_row()])

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]


def test_build_rank_links_does_not_cross_match_different_tournaments() -> None:
    """Same rank pair, different official_tournament_id -> no candidate, no cross-match."""
    uk_df = pd.DataFrame([_uk_row(source_event_key="2025_1_other_event")])  # -> official id 999
    sackmann_df = pd.DataFrame([_sk_row()])  # tourney_id "2025-520" -> official id 520

    accepted, ambiguous, unmatched = build_rank_links(uk_df, sackmann_df, _tournament_mapper())

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]


def test_build_rank_links_raises_on_duplicate_source_match_key() -> None:
    uk_df = pd.DataFrame(
        [
            _uk_row(source_match_key="dup"),
            _uk_row(source_match_key="dup"),
        ]
    )
    sackmann_df = pd.DataFrame([_sk_row()])

    with pytest.raises(ValueError, match="source_match_key"):
        build_rank_links(uk_df, sackmann_df, _tournament_mapper())


def test_build_rank_links_raises_on_duplicate_canonical_match_key() -> None:
    uk_df = pd.DataFrame([_uk_row()])
    sackmann_df = pd.DataFrame(
        [
            _sk_row(tourney_id="2025-520", match_num=300),
            _sk_row(tourney_id="2025-520", match_num=300),
        ]
    )

    with pytest.raises(ValueError, match="canonical_match_key"):
        build_rank_links(uk_df, sackmann_df, _tournament_mapper())


def test_classify_rank_candidates_detects_round_disagreement() -> None:
    candidates = pd.DataFrame(
        [
            {
                "source_match_key": "uk_1",
                "canonical_match_key": "sk_1",
                "round_uk": "F",
                "round_sk": "SF",
                "winner_rank_points_uk": 10000,
                "winner_rank_points_sk": 9800,
                "loser_rank_points_uk": 3000,
                "loser_rank_points_sk": 3000,
            }
        ]
    )

    result = classify_rank_candidates(candidates)

    assert result.iloc[0]["is_unique"]
    assert not result.iloc[0]["round_agrees"]
    assert result.iloc[0]["winner_rank_points_diff"] == 200
    assert result.iloc[0]["loser_rank_points_diff"] == 0


def test_classify_rank_candidates_handles_mismatched_round_categories() -> None:
    """round_uk/round_sk are each independently-built `category` dtype - comparing them
    must not raise even when the two sides' category sets differ (real-world bug: some
    seasons' UK/Sackmann round codes don't fully overlap, e.g. no "RR" in one side)."""
    candidates = pd.DataFrame(
        [
            {
                "source_match_key": "uk_1",
                "canonical_match_key": "sk_1",
                "round_uk": "F",
                "round_sk": "F",
                "winner_rank_points_uk": 10000,
                "winner_rank_points_sk": 10000,
                "loser_rank_points_uk": 3000,
                "loser_rank_points_sk": 3000,
            }
        ]
    )
    candidates["round_uk"] = candidates["round_uk"].astype(pd.CategoricalDtype(categories=["F", "SF"]))
    candidates["round_sk"] = candidates["round_sk"].astype(pd.CategoricalDtype(categories=["F", "RR"]))

    result = classify_rank_candidates(candidates)

    assert result.iloc[0]["round_agrees"]


def test_generate_rank_candidates_excludes_rows_without_official_tournament_id() -> None:
    uk_linked = pd.DataFrame([{**_uk_row(), "official_tournament_id": pd.NA}])
    sackmann_linked = pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])

    candidates = generate_rank_candidates(uk_linked, sackmann_linked)

    assert candidates.empty


# --------------------------------------------------------------------------- #
# Pass 2: name-pair compatibility helpers
# --------------------------------------------------------------------------- #


def test_parse_tennis_data_name_handles_multi_word_surname_and_initials() -> None:
    assert parse_tennis_data_name("Fritz T.").surname == "fritz"
    assert parse_tennis_data_name("Fritz T.").initials == "t"
    assert parse_tennis_data_name("Ugo Carabelli C.").surname == "ugo carabelli"
    assert parse_tennis_data_name("Zhang Zh.").initials == "zh"


def test_parse_tennis_data_name_handles_multi_part_initials() -> None:
    """Multi-part initials can be one fused token ("J.J.") or separately spaced
    ("J. P.") - both must parse to a surname of just the player's last name."""
    assert parse_tennis_data_name("Wolf J.J.") == ("wolf", "jj")
    assert parse_tennis_data_name("Varillas J. P.") == ("varillas", "jp")
    assert parse_tennis_data_name("Bu Y.") == ("bu", "y")  # short real surname, not initials


def test_normalize_name_transliterates_non_decomposing_latin_extended_letters() -> None:
    """NFKD doesn't decompose these into base letter + accent - they'd otherwise be dropped."""
    assert normalize_name("\u0110okovi\u0107") == "dokovic"
    assert normalize_name("\u0141ukasz") == "lukasz"
    assert normalize_name("Bj\u00f8rn") == "bjorn"


@pytest.mark.parametrize(
    "source_name,canonical_name,expected",
    [
        # 1: abbreviated winner/loser names match full canonical names
        ("Fritz T.", "Taylor Fritz", True),
        ("Nava E.", "Emilio Nava", True),
        # 9: multi-character abbreviation
        ("Zhang Zh.", "Zhizhen Zhang", True),
        # 7: comparing against the *other* player must not match
        ("Fritz T.", "Emilio Nava", False),
        # wrong initial
        ("Fritz Z.", "Taylor Fritz", False),
        # multi-word surname
        ("Ugo Carabelli C.", "Camilo Ugo Carabelli", True),
        # hyphenated surname
        ("Auger-Aliassime F.", "Felix Auger-Aliassime", True),
        # hyphenated source surname vs. Sackmann's space-separated equivalent
        ("Auger-Aliassime F.", "Felix Auger Aliassime", True),
        # spaced source surname vs. Sackmann's fused-word equivalent
        ("O Connell C.", "Christopher Oconnell", True),
        # multi-part initials, fused in the source, spaced in canonical given names
        ("Wolf J.J.", "J J Wolf", True),
        # multi-part initials, spaced in both
        ("Varillas J. P.", "Juan Pablo Varillas", True),
        # non-decomposing Latin-Extended letter (đ) in both source and canonical
        ("\u0110okovi\u0107 N.", "Novak \u0110okovi\u0107", True),
    ],
)
def test_player_name_compatible(source_name: str, canonical_name: str, expected: bool) -> None:
    assert player_name_compatible(source_name, canonical_name) is expected


# --------------------------------------------------------------------------- #
# Pass 2: build_name_pair_links
# --------------------------------------------------------------------------- #


def test_build_name_pair_links_accepts_abbreviated_vs_full_name_pair() -> None:
    """Case 1: unique name pair within tournament+round, both ranks present and agree."""
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert len(accepted) == 1
    row = accepted.iloc[0]
    assert row["source_match_key"] == "uk_1"
    assert row["canonical_match_key"] == "2025-520_300"
    assert row["match_method"] == MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR
    assert not row["review_flag"]
    assert pd.isna(row["data_quality_flag"])
    assert row["winner_rank_agrees"]
    assert row["loser_rank_agrees"]
    assert ambiguous.empty
    assert unmatched.empty


def test_build_name_pair_links_accepts_with_missing_winner_rank() -> None:
    """Case 2: winner rank missing on the UK side, name pair still unique."""
    uk_residual = pd.DataFrame([{**_uk_row(winner_rank=None), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert len(accepted) == 1
    assert accepted.iloc[0]["data_quality_flag"] == "missing_rank"
    assert pd.isna(accepted.iloc[0]["winner_rank_agrees"])
    assert accepted.iloc[0]["loser_rank_agrees"]


def test_build_name_pair_links_accepts_with_missing_loser_rank() -> None:
    """Case 3: loser rank missing on the UK side, name pair still unique."""
    uk_residual = pd.DataFrame([{**_uk_row(loser_rank=None), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert len(accepted) == 1
    assert accepted.iloc[0]["data_quality_flag"] == "missing_rank"
    assert accepted.iloc[0]["winner_rank_agrees"]
    assert pd.isna(accepted.iloc[0]["loser_rank_agrees"])


def test_build_name_pair_links_accepts_despite_rank_mismatch() -> None:
    """Case 4: ranks present on both sides but disagree - still accepted, flagged."""
    uk_residual = pd.DataFrame([{**_uk_row(loser_rank=968), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(loser_rank=101), "official_tournament_id": 520}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert len(accepted) == 1
    assert accepted.iloc[0]["data_quality_flag"] == "rank_mismatch"
    assert accepted.iloc[0]["winner_rank_agrees"]
    assert not accepted.iloc[0]["loser_rank_agrees"]


def test_build_name_pair_links_does_not_accept_ambiguous_name_pair() -> None:
    """Case 5: two Sackmann rows in the same tournament+round both look name-compatible."""
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame(
            [
                {**_sk_row(match_num=300), "official_tournament_id": 520},
                {**_sk_row(match_num=301, loser_name="Emilio Nava Jr"), "official_tournament_id": 520},
            ]
        )
    )
    # both canonical rows have a surname-compatible loser name for "Nava E."
    sackmann_residual.loc[1, "loser_name"] = "Emilio Nava"

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert accepted.empty
    assert set(ambiguous["canonical_match_key"]) == {"2025-520_300", "2025-520_301"}
    assert (ambiguous["source_candidate_count"] == 2).all()


def test_build_name_pair_links_does_not_cross_match_different_tournaments() -> None:
    """Case 6: same names, different official_tournament_id -> no candidate at all."""
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(), "official_tournament_id": 999}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]


def test_build_name_pair_links_does_not_cross_match_different_rounds() -> None:
    """Same tournament, same compatible name pair, different round -> no candidate at all."""
    uk_residual = pd.DataFrame([{**_uk_row(round="F"), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(round="SF"), "official_tournament_id": 520}])
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]


def test_build_name_pair_links_raises_on_duplicate_source_match_key() -> None:
    uk_residual = pd.DataFrame(
        [
            {**_uk_row(source_match_key="dup"), "official_tournament_id": 520},
            {**_uk_row(source_match_key="dup"), "official_tournament_id": 520},
        ]
    )
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame([{**_sk_row(), "official_tournament_id": 520}])
    )

    with pytest.raises(ValueError, match="source_match_key"):
        build_name_pair_links(uk_residual, sackmann_residual)


def test_build_name_pair_links_raises_on_duplicate_canonical_match_key() -> None:
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame(
            [
                {**_sk_row(match_num=300), "official_tournament_id": 520},
                {**_sk_row(match_num=300), "official_tournament_id": 520},
            ]
        )
    )

    with pytest.raises(ValueError, match="canonical_match_key"):
        build_name_pair_links(uk_residual, sackmann_residual)


def test_generate_name_pair_candidates_does_not_match_reversed_winner_loser() -> None:
    """Case 7: swapping winner/loser on the canonical side must not produce a candidate."""
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame(
            [
                {
                    **_sk_row(winner_name="Emilio Nava", loser_name="Taylor Fritz"),
                    "official_tournament_id": 520,
                }
            ]
        )
    )

    candidates = generate_name_pair_candidates(uk_residual, sackmann_residual)

    assert candidates.empty


def test_build_rank_and_name_links_does_not_reuse_pass1_consumed_canonical_match() -> None:
    """Case 8: a Sackmann row already accepted by Pass 1 must not reappear in Pass 2."""
    uk_df = pd.DataFrame(
        [
            _uk_row(source_match_key="uk_1"),  # resolvable by Pass 1 (ranks match)
            _uk_row(
                source_match_key="uk_2",
                winner_rank=None,  # only resolvable by Pass 2 (name pair)
                winner_name="Munar J.",
                loser_name="Martin D.",
            ),
        ]
    )
    sackmann_df = pd.DataFrame(
        [
            _sk_row(match_num=300),
            _sk_row(match_num=301, winner_name="Jaume Munar", loser_name="Dan Martin", winner_rank=51),
        ]
    )

    accepted, ambiguous, unmatched = build_rank_and_name_links(uk_df, sackmann_df, _tournament_mapper())

    assert len(accepted) == 2
    methods_by_key = dict(zip(accepted["source_match_key"], accepted["match_method"], strict=True))
    assert methods_by_key["uk_1"] == MATCH_METHOD_TOURNAMENT_RANK_UNIQUE
    assert methods_by_key["uk_2"] == MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR
    # Pass-1's canonical match is not reconsidered/duplicated by Pass 2
    assert accepted["canonical_match_key"].tolist().count("2025-520_300") == 1
    assert unmatched.empty


def test_build_rank_and_name_links_resolves_pass1_ambiguous_row_via_name_pair() -> None:
    """A Pass-1 rank-ambiguous UK row can still be uniquely resolved in Pass 2.

    Two Sackmann rows share the UK row's rank pair (ambiguous in Pass 1), but
    only one shares its round, so Pass 2's tournament+round+name-pair block
    resolves it uniquely - a rank ambiguity must not be a dead end.
    """
    uk_df = pd.DataFrame([_uk_row(source_match_key="uk_1", round="F")])
    sackmann_df = pd.DataFrame(
        [
            _sk_row(match_num=300, round="F"),  # true match: same round, compatible names
            _sk_row(
                match_num=301,
                round="SF",
                winner_name="Someone Else",
                loser_name="Another Person",
            ),
        ]
    )

    accepted, ambiguous, unmatched = build_rank_and_name_links(uk_df, sackmann_df, _tournament_mapper())

    assert len(accepted) == 1
    row = accepted.iloc[0]
    assert row["source_match_key"] == "uk_1"
    assert row["canonical_match_key"] == "2025-520_300"
    assert row["match_method"] == MATCH_METHOD_TOURNAMENT_ROUND_NAME_PAIR
    # the Pass-1 rank ambiguity between match_num 300 and 301 is still preserved for inspection
    assert set(ambiguous["canonical_match_key"]) == {"2025-520_300", "2025-520_301"}
    assert unmatched.empty


def test_build_name_pair_links_leaves_unmatched_rows_unmatched() -> None:
    """Case 10: a residual row with no compatible counterpart stays unmatched."""
    uk_residual = pd.DataFrame([{**_uk_row(), "official_tournament_id": 520}])
    sackmann_residual = add_sackmann_match_key(
        pd.DataFrame(
            [
                {
                    **_sk_row(winner_name="Someone Else", loser_name="Another Person"),
                    "official_tournament_id": 520,
                }
            ]
        )
    )

    accepted, ambiguous, unmatched = build_name_pair_links(uk_residual, sackmann_residual)

    assert accepted.empty
    assert ambiguous.empty
    assert unmatched["source_match_key"].tolist() == ["uk_1"]
