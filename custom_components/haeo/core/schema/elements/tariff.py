"""Tariff element schema definitions.

A tariff defines pricing rules for power flowing between source and destination
nodes. Tags are assigned automatically — the user configures sources, destinations,
and prices. The compilation step handles VLAN assignment and segment injection.
"""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.TARIFF

# Config keys
SECTION_ENDPOINTS: Final = "endpoints"
SECTION_TAG_PRICING: Final = "tag_pricing"

CONF_SOURCES: Final = "sources"
CONF_DESTINATIONS: Final = "destinations"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
    }
)


class TariffEndpointsConfig(TypedDict):
    """Endpoint configuration for tariff source/destination selection."""

    sources: list[str]  # Node names, or ["*"] for "any"
    destinations: list[str]  # Node names, or ["*"] for "any"


class TariffEndpointsData(TypedDict):
    """Loaded endpoint values."""

    sources: list[str]
    destinations: list[str]


class TariffPricingConfig(TypedDict, total=False):
    """Pricing configuration for a tariff."""

    price_source_target: EntityValue | ConstantValue | NoneValue
    price_target_source: EntityValue | ConstantValue | NoneValue


class TariffPricingData(TypedDict, total=False):
    """Loaded pricing values for a tariff."""

    price_source_target: NDArray[np.floating[Any]] | float
    price_target_source: NDArray[np.floating[Any]] | float


class TariffConfigSchema(CommonConfig):
    """Tariff element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.TARIFF]
    endpoints: TariffEndpointsConfig
    tag_pricing: Annotated[
        TariffPricingConfig,
        SectionHints(
            {
                CONF_PRICE_SOURCE_TARGET: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="-",
                    time_series=True,
                ),
                CONF_PRICE_TARGET_SOURCE: FieldHint(
                    output_type=OutputType.PRICE,
                    direction="+",
                    time_series=True,
                ),
            }
        ),
    ]


class TariffConfigData(CommonData):
    """Tariff element configuration with loaded values."""

    element_type: Literal[ElementType.TARIFF]
    endpoints: TariffEndpointsData
    tag_pricing: TariffPricingData


__all__ = [
    "CONF_DESTINATIONS",
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCES",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ENDPOINTS",
    "SECTION_TAG_PRICING",
    "TariffConfigData",
    "TariffConfigSchema",
    "TariffEndpointsConfig",
    "TariffEndpointsData",
    "TariffPricingConfig",
    "TariffPricingData",
]
