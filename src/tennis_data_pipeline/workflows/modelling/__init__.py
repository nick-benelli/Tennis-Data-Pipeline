"""Curated Sackmann+UK merged dataset for downstream EDA/modelling (external repos)."""

from .dataset import (
    CORE_SACKMANN_COLUMNS,
    LINKAGE_QA_COLUMNS,
    MODEL_COLUMNS,
    UK_SUPPLEMENTAL_COLUMNS,
    build_match_dataset,
    build_match_dataset_for_years,
    discover_available_years,
)

__all__ = [
    "CORE_SACKMANN_COLUMNS",
    "LINKAGE_QA_COLUMNS",
    "MODEL_COLUMNS",
    "UK_SUPPLEMENTAL_COLUMNS",
    "build_match_dataset",
    "build_match_dataset_for_years",
    "discover_available_years",
]
