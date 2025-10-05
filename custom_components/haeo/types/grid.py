"""Grid element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from custom_components.haeo.schema.fields import NameField, PowerField, PricesSensorsAndForecastsField


@dataclass
class GridConfig:
    """Grid element configuration."""

    name: NameField

    import_price: PricesSensorsAndForecastsField
    export_price: PricesSensorsAndForecastsField

    import_limit: PowerField | None = None
    export_limit: PowerField | None = None

    element_type: Literal["grid"] = "grid"
