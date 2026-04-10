"""Tariff element schema definitions.

A tariff defines tagged power flow pricing between two nodes.
When configured, it creates a parallel connection with tag_pricing segments
that add costs to power flowing between the specified nodes.
"""

from typing import Annotated, Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import ConnectionTarget, ConstantValue, EntityValue, NoneValue
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.field_hints import FieldHint, SectionHints
from custom_components.haeo.core.schema.sections import CommonConfig, CommonData

ELEMENT_TYPE = ElementType.TARIFF

# Config keys
SECTION_ENDPOINTS: Final = "endpoints"
SECTION_TAG_PRICING: Final = "tag_pricing"

CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_TAG: Final = "tag"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset(
    {
        CONF_PRICE_SOURCE_TARGET,
        CONF_PRICE_TARGET_SOURCE,
    }
)


class TariffEndpointsConfig(TypedDict):
    """Endpoint configuration for tariff source/target pairs."""

    source: ConnectionTarget
    target: ConnectionTarget


class TariffEndpointsData(TypedDict):
    """Loaded endpoint values."""

    source: ConnectionTarget
    target: ConnectionTarget


class TariffTagConfig(TypedDict):
    """Tag and pricing configuration for a tariff."""

    tag: int
    price_source_target: NotRequired[EntityValue | ConstantValue | NoneValue]
    price_target_source: NotRequired[EntityValue | ConstantValue | NoneValue]


class TariffTagData(TypedDict):
    """Loaded tag and pricing values for a tariff."""

    tag: int
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float]
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float]


class TariffConfigSchema(CommonConfig):
    """Tariff element configuration as stored in Home Assistant."""

    element_type: Literal[ElementType.TARIFF]
    endpoints: TariffEndpointsConfig
    tag_pricing: Annotated[
        TariffTagConfig,
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
    tag_pricing: TariffTagData


__all__ = [
    "CONF_PRICE_SOURCE_TARGET",
    "CONF_PRICE_TARGET_SOURCE",
    "CONF_SOURCE",
    "CONF_TAG",
    "CONF_TARGET",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ENDPOINTS",
    "SECTION_TAG_PRICING",
    "TariffConfigData",
    "TariffConfigSchema",
    "TariffEndpointsConfig",
    "TariffEndpointsData",
    "TariffTagConfig",
    "TariffTagData",
]
