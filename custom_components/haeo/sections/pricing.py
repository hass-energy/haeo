"""Shared definitions for pricing configuration sections."""

from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.flows.field_schema import SectionDefinition

SECTION_PRICING: Final = "pricing"

type PricingValueConfig = list[str] | str | float
type PricingValueData = NDArray[np.floating[Any]] | float


class PricingConfig(TypedDict, total=False):
    """Pricing configuration across element types."""

    early_charge_incentive: PricingValueConfig
    discharge_cost: PricingValueConfig
    import_price: PricingValueConfig
    export_price: PricingValueConfig
    price_production: PricingValueConfig
    price_source_target: PricingValueConfig
    price_target_source: PricingValueConfig


class PricingData(TypedDict, total=False):
    """Loaded pricing values across element types."""

    early_charge_incentive: PricingValueData
    discharge_cost: PricingValueData
    import_price: PricingValueData
    export_price: PricingValueData
    price_production: PricingValueData
    price_source_target: PricingValueData
    price_target_source: PricingValueData


def pricing_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard pricing section definition."""
    return SectionDefinition(key=SECTION_PRICING, fields=fields, collapsed=collapsed)


def build_pricing_fields() -> dict[str, tuple[vol.Marker, Any]]:
    """Build pricing field entries for config flows."""
    return {}


__all__ = [  # noqa: RUF022
    "PricingConfig",
    "PricingData",
    "SECTION_PRICING",
    "build_pricing_fields",
    "pricing_section",
]
