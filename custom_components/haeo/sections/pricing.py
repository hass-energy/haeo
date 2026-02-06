"""Shared definitions for pricing configuration sections."""

from collections.abc import Mapping
from typing import Any, Final, TypedDict

import numpy as np
from numpy.typing import NDArray
import voluptuous as vol

from custom_components.haeo.elements.field_schema import FieldSchemaInfo
from custom_components.haeo.elements.input_fields import InputFieldSection
from custom_components.haeo.flows.field_schema import SectionDefinition, build_choose_field_entries
from custom_components.haeo.schema import ConstantValue, EntityValue, NoneValue

SECTION_PRICING: Final = "pricing"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"
CONF_DEMAND_WINDOW_SOURCE_TARGET: Final = "demand_window_source_target"
CONF_DEMAND_WINDOW_TARGET_SOURCE: Final = "demand_window_target_source"
CONF_DEMAND_PRICE_SOURCE_TARGET: Final = "demand_price_source_target"
CONF_DEMAND_PRICE_TARGET_SOURCE: Final = "demand_price_target_source"
CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET: Final = "demand_current_energy_source_target"
CONF_DEMAND_CURRENT_ENERGY_TARGET_SOURCE: Final = "demand_current_energy_target_source"
CONF_DEMAND_BLOCK_HOURS: Final = "demand_block_hours"
CONF_DEMAND_DAYS: Final = "demand_days"


class PricingConfig(TypedDict, total=False):
    """Directional pricing configuration for power transfer."""

    price_source_target: EntityValue | ConstantValue | NoneValue
    price_target_source: EntityValue | ConstantValue | NoneValue
    demand_window_source_target: EntityValue | ConstantValue | NoneValue
    demand_window_target_source: EntityValue | ConstantValue | NoneValue
    demand_price_source_target: EntityValue | ConstantValue | NoneValue
    demand_price_target_source: EntityValue | ConstantValue | NoneValue
    demand_current_energy_source_target: EntityValue | ConstantValue | NoneValue
    demand_current_energy_target_source: EntityValue | ConstantValue | NoneValue
    demand_block_hours: EntityValue | ConstantValue | NoneValue
    demand_days: EntityValue | ConstantValue | NoneValue


class PricingData(TypedDict, total=False):
    """Loaded directional pricing values."""

    price_source_target: NDArray[np.floating[Any]] | float
    price_target_source: NDArray[np.floating[Any]] | float
    demand_window_source_target: NDArray[np.floating[Any]] | float
    demand_window_target_source: NDArray[np.floating[Any]] | float
    demand_price_source_target: NDArray[np.floating[Any]] | float
    demand_price_target_source: NDArray[np.floating[Any]] | float
    demand_current_energy_source_target: NDArray[np.floating[Any]] | float
    demand_current_energy_target_source: NDArray[np.floating[Any]] | float
    demand_block_hours: float
    demand_days: float


def pricing_section(fields: tuple[str, ...], *, collapsed: bool = False) -> SectionDefinition:
    """Return the standard pricing section definition."""
    return SectionDefinition(key=SECTION_PRICING, fields=fields, collapsed=collapsed)


def build_pricing_fields(
    input_fields: InputFieldSection,
    *,
    field_schema: Mapping[str, FieldSchemaInfo],
    inclusion_map: dict[str, list[str]],
    current_data: Mapping[str, Any] | None = None,
) -> dict[str, tuple[vol.Marker, Any]]:
    """Build pricing field entries for config flows."""
    if not input_fields:
        return {}
    return build_choose_field_entries(
        input_fields,
        field_schema=field_schema,
        inclusion_map=inclusion_map,
        current_data=current_data,
    )


__all__ = [
    "CONF_DEMAND_BLOCK_HOURS",
    "CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET",
    "CONF_DEMAND_CURRENT_ENERGY_TARGET_SOURCE",
    "CONF_DEMAND_DAYS",
    "CONF_DEMAND_PRICE_SOURCE_TARGET",
    "CONF_DEMAND_PRICE_TARGET_SOURCE",
    "CONF_DEMAND_WINDOW_SOURCE_TARGET",
    "CONF_DEMAND_WINDOW_TARGET_SOURCE",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "SECTION_PRICING",
    "PricingConfig",
    "PricingData",
    "build_pricing_fields",
    "pricing_section",
]
