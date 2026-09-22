"""Application configuration schema."""

from __future__ import annotations
from .api import ApiConfig
from .logging import LoggingConfig
from .paths import PathsConfig
from .uk import TennisDataUKConfig
from .sackmann import SackmannConfig
from .mapping import MappingConfig
from .wta_api import WtaApiConfig
from .base import StrictModel
from pydantic import Field


class AppConfig(StrictModel):
    """Validated config root model."""

    api: ApiConfig = Field(default_factory=ApiConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    tennis_data_uk: TennisDataUKConfig = Field(default_factory=TennisDataUKConfig)
    sackmann: SackmannConfig = Field(default_factory=SackmannConfig)
    mapping: MappingConfig = Field(default_factory=MappingConfig)
    wta_api: WtaApiConfig = Field(default_factory=WtaApiConfig)


__all__ = [
    "AppConfig",
]
