"""Shared definitions for pricing configuration sections."""

from collections.abc import Mapping
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries

SECTION_PRICING: Final = "pricing"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

type PricingValueConfig = list[str] | str | float
type PricingValueData = NDArray[np.floating[Any]] | float


class PricingConfig(TypedDict, total=False):
    """Directional pricing configuration for power transfer."""

    price_source_target: PricingValueConfig
    price_target_source: PricingValueConfig


class PricingData(TypedDict, total=False):
    """Loaded directional pricing values."""

    price_source_target: PricingValueData
    price_target_source: PricingValueData


def pricing_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard pricing section definition."""
    return SectionDefinition(key=SECTION_PRICING, fields=fields, collapsed=collapsed)


def build_pricing_fields(
    input_fields: InputFieldSection,
    *,
    optional_fields: frozenset[str],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build pricing field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        optional_fields=optional_fields,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "SECTION_PRICING",
    "PricingConfig",
    "PricingData",
    "build_pricing_fields",
    "pricing_section",
]
