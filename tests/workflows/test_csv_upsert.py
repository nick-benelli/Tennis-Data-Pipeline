"""Tests for the shared CSV-upsert helper (`workflows._csv_upsert`)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tennis_data_pipeline.workflows._csv_upsert import upsert_csv


def test_upsert_csv_creates_file_when_none_exists(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    rows = pd.DataFrame([{"key": "a", "value": 1}])

    result = upsert_csv(path, rows, key_columns=["key"])

    assert path.exists()
    assert result.to_dict("records") == [{"key": "a", "value": 1}]


def test_upsert_csv_appends_new_rows_without_touching_existing_ones(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    upsert_csv(path, pd.DataFrame([{"key": "a", "value": 1}]), key_columns=["key"])

    result = upsert_csv(path, pd.DataFrame([{"key": "b", "value": 2}]), key_columns=["key"])

    assert sorted(result.to_dict("records"), key=lambda r: r["key"]) == [
        {"key": "a", "value": 1},
        {"key": "b", "value": 2},
    ]


def test_upsert_csv_keep_last_lets_new_rows_win_on_key_conflict(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    upsert_csv(path, pd.DataFrame([{"key": "a", "value": 1}]), key_columns=["key"])

    result = upsert_csv(
        path, pd.DataFrame([{"key": "a", "value": 999}]), key_columns=["key"], keep="last"
    )

    assert result.to_dict("records") == [{"key": "a", "value": 999}]


def test_upsert_csv_keep_first_protects_existing_rows_from_being_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    upsert_csv(path, pd.DataFrame([{"key": "a", "value": 1}]), key_columns=["key"])

    result = upsert_csv(
        path, pd.DataFrame([{"key": "a", "value": 999}]), key_columns=["key"], keep="first"
    )

    assert result.to_dict("records") == [{"key": "a", "value": 1}]


def test_upsert_csv_fills_missing_num_columns_with_zero_not_nan(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    upsert_csv(path, pd.DataFrame([{"key": "a", "num_matches": 5}]), key_columns=["key"])

    # Second run's rows don't carry num_matches at all (e.g. a status not seen this time).
    result = upsert_csv(path, pd.DataFrame([{"key": "b"}]), key_columns=["key"])

    assert result.set_index("key")["num_matches"].to_dict() == {"a": 5.0, "b": 0.0}


def test_upsert_csv_sorts_output_by_key_columns(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    rows = pd.DataFrame([{"key": "b", "value": 2}, {"key": "a", "value": 1}])

    result = upsert_csv(path, rows, key_columns=["key"])

    assert result["key"].tolist() == ["a", "b"]


def test_upsert_csv_supports_composite_key_columns(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    upsert_csv(
        path,
        pd.DataFrame([{"year": 2020, "id": "x", "value": 1}, {"year": 2021, "id": "x", "value": 2}]),
        key_columns=["year", "id"],
    )

    result = upsert_csv(
        path, pd.DataFrame([{"year": 2020, "id": "x", "value": 999}]), key_columns=["year", "id"]
    )

    assert sorted(result.to_dict("records"), key=lambda r: r["year"]) == [
        {"year": 2020, "id": "x", "value": 999},
        {"year": 2021, "id": "x", "value": 2},
    ]
