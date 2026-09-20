"""Cross-tour schema-parity tests: ATP and WTA must share the same clean-output columns."""

from __future__ import annotations

from tennis_data_pipeline.handler.uk.cleaner import atp_cols, wta_cols


def test_atp_and_wta_column_order_match() -> None:
    """ATP and WTA clean output use the exact same column order."""
    assert atp_cols.COLUMN_ORDER == wta_cols.COLUMN_ORDER


def test_atp_and_wta_odds_columns_match() -> None:
    """ATP and WTA clean output expose the exact same odds columns."""
    assert atp_cols.ODDS_COLS == wta_cols.ODDS_COLS


def test_wta_expected_rounds_is_superset_of_atp() -> None:
    """WTA's expected rounds are ATP's plus 'BR' (third-place playoff)."""
    # WTA adds "BR" (third-place playoff); everything else is shared.
    assert wta_cols.EXPECTED_ROUNDS - atp_cols.EXPECTED_ROUNDS == {"BR"}


def test_wta_status_map_is_superset_of_atp() -> None:
    """WTA's status map is ATP's plus 'Cancelled'."""
    # WTA adds "Cancelled"; everything else is shared.
    assert set(wta_cols.STATUS_MAP) - set(atp_cols.STATUS_MAP) == {"Cancelled"}
