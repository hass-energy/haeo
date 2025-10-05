"""Grid element configuration for HAEO integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .fields import NameField, PowerField, PriceLiveAndForecastField


@dataclass
class GridConfig:
    """Grid element configuration."""

    name: NameField

    import_price: PriceLiveAndForecastField
    export_price: PriceLiveAndForecastField

    import_limit: PowerField | None = None
    export_limit: PowerField | None = None

    element_type: Literal["grid"] = "grid"
