"""Application configuration schema."""

from __future__ import annotations

from pydantic import Field

from .api import ApiConfig
from .base import StrictModel
from .linked import LinkedConfig
from .logging import LoggingConfig
from .mapping import MappingConfig
from .paths import PathsConfig
from .sackmann import SackmannConfig
from .uk import TennisDataUKConfig
from .wta_api import WtaApiConfig


class AppConfig(StrictModel):
    """Validated config root model."""

    api: ApiConfig = Field(default_factory=ApiConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    tennis_data_uk: TennisDataUKConfig = Field(default_factory=TennisDataUKConfig)
    sackmann: SackmannConfig = Field(default_factory=SackmannConfig)
    mapping: MappingConfig = Field(default_factory=MappingConfig)
    linked: LinkedConfig = Field(default_factory=LinkedConfig)
    wta_api: WtaApiConfig = Field(default_factory=WtaApiConfig)


__all__ = [
    "AppConfig",
]
