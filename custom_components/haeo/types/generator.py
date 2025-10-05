"""Generator element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import BooleanField, NameField, PowerForecastField, PriceField


@dataclass
class GeneratorConfig:
    """Generator element configuration."""

    name: NameField

    forecast: PowerForecastField

    price_production: PriceField | None = None
    curtailment: BooleanField = False

    element_type: Literal["generator"] = "generator"
