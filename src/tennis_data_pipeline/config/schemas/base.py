"""Base schema definitions for the tennis data pipeline."""

from __future__ import annotations
import re
from pydantic import BaseModel, ConfigDict
from typing import Any


_ENV_PLACEHOLDER_PATTERN = re.compile(r"^\$\{[^}]+\}$")


def _is_unresolved_env_placeholder(value: Any) -> bool:
    return isinstance(value, str) and bool(_ENV_PLACEHOLDER_PATTERN.fullmatch(value))


def _field_default(model_cls: type[BaseModel], field_name: str) -> Any:
    """Return a model field default in a type-checker-friendly way."""
    return model_cls.__pydantic_fields__[field_name].default


def _normalize_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value) if value is not None else default


class StrictModel(BaseModel):
    """Base model that rejects unknown config keys."""

    model_config = ConfigDict(extra="forbid")
