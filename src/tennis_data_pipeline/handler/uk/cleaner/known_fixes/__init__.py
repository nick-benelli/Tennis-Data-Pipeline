"""Known one-off and category-level data-error fixes for Tennis-Data UK raw data.

Two separate mechanisms, deliberately not unified:

- `MatchFix` - a hand-verified correction to exactly one match. Every fix must
  assert it still matches exactly one row before applying; a fix that
  silently matches zero rows after a future re-scrape or column rename is a
  bug we want to hear about immediately, not one that quietly stops applying.
- Category-typo fixes (e.g. `fix_wta_category_typos`) - a whole mislabeled
  *value* across many rows, which doesn't fit the single-match shape above.

Split into `_shared.py` (the `MatchFix` contract), `atp.py`, and `wta.py` -
re-exported here so `known_fixes.X` keeps working for existing callers.
"""

from tennis_data_pipeline.handler.uk.cleaner.known_fixes._shared import (
    MatchFix,
    apply_match_fixes,
)
from tennis_data_pipeline.handler.uk.cleaner.known_fixes.atp import (
    ATP_MATCH_FIXES,
    fix_atp_category_typos,
)
from tennis_data_pipeline.handler.uk.cleaner.known_fixes.wta import (
    WTA_MATCH_FIXES,
    fix_wta_category_typos,
)

__all__ = [
    "ATP_MATCH_FIXES",
    "WTA_MATCH_FIXES",
    "MatchFix",
    "apply_match_fixes",
    "fix_atp_category_typos",
    "fix_wta_category_typos",
]
