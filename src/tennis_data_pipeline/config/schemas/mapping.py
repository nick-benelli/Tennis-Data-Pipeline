"""Mapping configuration schema."""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from tennis_data_pipeline.config.schemas.base import (
    StrictModel,
    _field_default,
    _is_unresolved_env_placeholder,
)


class MappingConfig(StrictModel):
    """Cross-source tournament id mapping settings (data/mapping/)."""

    tournament_dir_name: str = "tournaments"
    crosswalk_filename_template: str = "{tour}_tournament_crosswalk.csv"
    source_links_filename_template: str = "{tour}_tournament_source_links.csv"
    # Hand-maintained override table (see mapper.tournaments.match_uk_to_sackmann_tourneys).
    manual_matches_filename_template: str = "{tour}_tournament_manual_matches.csv"
    # Candidate matches scoring below this are treated as "no match" (see mapper.tournaments).
    min_match_score: float = 0.5

    # Pass-0 hand-maintained match-level override table (see mapper.matches.build_manual_links).
    match_dir_name: str = "matches"
    match_manual_links_filename_template: str = "{tour}_manual_links.csv"

    @field_validator("min_match_score", mode="before")
    @classmethod
    def normalize_min_match_score(cls, value: Any) -> float:
        """Fall back to the default if unset/an unresolved env placeholder, else validate 0-1."""
        if value is None or _is_unresolved_env_placeholder(value):
            return _field_default(cls, "min_match_score")
        score = float(value)
        if not 0.0 <= score <= 1.0:
            raise ValueError("mapping.min_match_score must be between 0 and 1")
        return score
