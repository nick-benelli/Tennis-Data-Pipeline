"""Tests for the shared CLI year-parsing helper (`tennis_data_pipeline.cli`)."""

from __future__ import annotations

import argparse

import pytest

from tennis_data_pipeline.cli import parse_years


def test_parse_years_expands_a_single_year() -> None:
    assert parse_years(["2022"]) == [2022]


def test_parse_years_expands_a_range() -> None:
    assert parse_years(["2010-2012"]) == [2010, 2011, 2012]


def test_parse_years_deduplicates_and_sorts_a_mix_of_years_and_ranges() -> None:
    assert parse_years(["2022", "2019", "2010-2012", "2011"]) == [2010, 2011, 2012, 2019, 2022]


def test_parse_years_strips_whitespace_around_tokens() -> None:
    assert parse_years([" 2022 ", " 2010-2011 "]) == [2010, 2011, 2022]


def test_parse_years_rejects_a_non_numeric_year() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid year 'abc'"):
        parse_years(["abc"])


def test_parse_years_rejects_a_non_numeric_range() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid year range"):
        parse_years(["2010-abc"])


def test_parse_years_rejects_a_range_with_start_after_end() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="start > end"):
        parse_years(["2015-2010"])
