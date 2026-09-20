"""Shared `MatchFix` infrastructure used by both the ATP and WTA fix registries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd


@dataclass(frozen=True)
class MatchFix:
    """A hand-verified, single-match correction to raw source data."""

    tour: str
    year: int
    description: str
    source_url: str | None
    match: Callable[[pd.DataFrame], pd.Series]
    apply: Callable[[pd.DataFrame, pd.Series], None]

    def apply_to(self, df: pd.DataFrame) -> None:
        """Apply this fix in place, raising if it no longer matches exactly one row."""
        mask = self.match(df)
        matched = int(mask.sum())
        if matched != 1:
            raise ValueError(
                f"Expected exactly 1 row for known fix '{self.description}' "
                f"({self.tour} {self.year}), found {matched}. The raw source "
                "may have changed; review before re-applying this fix."
            )
        self.apply(df, mask)


def apply_match_fixes(df: pd.DataFrame, tour: str, year: int, fixes: list[MatchFix]) -> pd.DataFrame:
    """Apply every registered single-match fix for `tour`/`year`, on a copy."""
    df = df.copy()
    for fix in fixes:
        if fix.tour == tour and fix.year == year:
            fix.apply_to(df)
    return df


def set_values(df: pd.DataFrame, mask: pd.Series, values: dict[str, object]) -> None:
    """Assign each column/value pair, casting to str first if the column is
    already string-dtyped (raw CSVs are sometimes read that way, e.g. by tests
    that skip the package's own numeric-coercion loader).
    """
    for col, value in values.items():
        col_value = str(value) if isinstance(df[col].dtype, pd.StringDtype) else value
        # `values` is deliberately heterogeneous (int/float/str corrections),
        # which pandas-stubs' .loc setter overloads can't express precisely.
        df.loc[mask, col] = cast(Any, col_value)
