"""Tests for shared (tour-agnostic) Tennis-Data UK cleaning helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from tennis_data_pipeline.handler.uk.cleaner import common


def _raw_event_rows() -> pd.DataFrame:
    """A single 32-draw tournament: 1st/2nd Round, QF, SF, Final."""
    rows = [
        {
            "ATP": 1,
            "Location": "Example",
            "Tournament": "Example Open",
            "Round": "1st Round",
        },
        {
            "ATP": 1,
            "Location": "Example",
            "Tournament": "Example Open",
            "Round": "2nd Round",
        },
        {
            "ATP": 1,
            "Location": "Example",
            "Tournament": "Example Open",
            "Round": "Quarterfinals",
        },
        {
            "ATP": 1,
            "Location": "Example",
            "Tournament": "Example Open",
            "Round": "Semifinals",
        },
        {
            "ATP": 1,
            "Location": "Example",
            "Tournament": "Example Open",
            "Round": "The Final",
        },
    ]
    df = pd.DataFrame(rows)
    df["Date"] = "2024-01-01"
    return df


def test_add_source_event_key_uses_given_id_column() -> None:
    """source_event_key is built from year/id/location/tournament, slugified."""
    df = _raw_event_rows()
    result = common.add_source_event_key(df, id_column="ATP")
    assert (result["source_event_key"] == "2024_1_example_example_open").all()


def test_assign_round_codes_counts_backward_from_qf() -> None:
    """Numbered rounds map to bracket codes by counting backward from QF."""
    df = common.add_source_event_key(_raw_event_rows(), id_column="ATP")
    result = common.assign_round_codes(df, common.BASE_ROUND_MAP)

    # 32-draw: 1st Round -> R32, 2nd Round -> R16, then the static entries.
    # Column stays "Round" (capitalized) here - renaming to "round" happens
    # later via COLUMN_MAP in clean_uk_atp_data/clean_uk_wta_data.
    assert list(result["Round"].astype(str)) == ["R32", "R16", "QF", "SF", "F"]


def test_assign_round_codes_scales_with_draw_size() -> None:
    """A 128-draw tournament's '1st Round' is R128, not R32."""
    rows = [
        {"ATP": 5, "Location": "Big", "Tournament": "Slam", "Round": r}
        for r in ["1st Round", "2nd Round", "3rd Round", "4th Round", "Quarterfinals"]
    ]
    df = pd.DataFrame(rows)
    df["Date"] = "2024-01-01"
    df = common.add_source_event_key(df, id_column="ATP")

    result = common.assign_round_codes(df, common.BASE_ROUND_MAP)
    assert list(result["Round"].astype(str)) == ["R128", "R64", "R32", "R16", "QF"]


def test_add_source_match_key() -> None:
    """source_match_key combines event key, date, round, and normalized player names."""
    df = pd.DataFrame(
        {
            "source_event_key": ["2024_1_example_example_open"],
            "match_date": pd.to_datetime(["2024-01-15"]),
            "round": ["F"],
            "winner_name": ["Player A."],
            "loser_name": ["Player B."],
        }
    )
    result = common.add_source_match_key(df)
    assert (
        result.loc[0, "source_match_key"] == "2024_1_example_example_open_2024-01-15_F_player_a_player_b"
    )


def test_fix_bad_odds_nulls_impossible_values() -> None:
    """Odds below 1.0 are nulled out rather than left as impossible values."""
    df = pd.DataFrame({"B365W": [1.5, 0.8, None], "B365L": [2.5, 3.0, 0.99]})
    result = common.fix_bad_odds(df, raw_odds_cols=["B365W", "B365L"])

    assert result["B365W"].tolist()[0] == 1.5
    assert pd.isna(result["B365W"].tolist()[1])
    assert pd.isna(result["B365L"].tolist()[2])


def test_ensure_columns_backfills_missing_as_nan() -> None:
    """A missing column is added and filled with NaN; an existing one is untouched."""
    df = pd.DataFrame({"odds_b365_winner": [1.5]})
    result = common.ensure_columns(df, ["odds_b365_winner", "odds_max_winner"])

    assert "odds_max_winner" in result.columns
    assert pd.isna(result.loc[0, "odds_max_winner"])
    assert result.loc[0, "odds_b365_winner"] == 1.5


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Roland Garros!", "roland_garros"),
        ("  Sao Paulo  ", "sao_paulo"),
    ],
)
def test_slugify(raw: str, expected: str) -> None:
    """slugify() lowercases, trims, and collapses non-alphanumerics to underscores."""
    assert common.slugify(raw) == expected


def test_load_raw_uk_csv_strips_whitespace_from_raw_string_cols(tmp_path) -> None:
    """Stray whitespace in Location/Tournament/Winner/Loser (e.g. "Dubai ") is stripped on load."""
    path = tmp_path / "raw.csv"
    pd.DataFrame(
        {
            "Date": ["2024-01-01"],
            "Location": ["Dubai "],
            "Tournament": [" Dubai Tennis Championships"],
            "Winner": ["Player A "],
            "Loser": [" Player B"],
        }
    ).to_csv(path, index=False)

    result = common.load_raw_uk_csv(path, 2024, int_cols=[], category_cols=[])

    assert result.loc[0, "Location"] == "Dubai"
    assert result.loc[0, "Tournament"] == "Dubai Tennis Championships"
    assert result.loc[0, "Winner"] == "Player A"
    assert result.loc[0, "Loser"] == "Player B"
