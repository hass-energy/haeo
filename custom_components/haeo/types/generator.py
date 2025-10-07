"""Generator element configuration for HAEO integration."""

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import BooleanField, NameField, PowerForecastsField, PriceField


@dataclass
class GeneratorConfig:
    """Generator element configuration."""

    name: NameField

    forecast: PowerForecastsField

    price_production: PriceField | None = None
    curtailment: BooleanField = False

    element_type: Literal["generator"] = "generator"
