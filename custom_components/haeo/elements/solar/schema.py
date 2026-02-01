"""Solar element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.sections import (
    CONF_FORECAST,
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_INPUTS,
    SECTION_PRICING,
    BasicNameConnectionConfig,
    BasicNameConnectionData,
    ForecastInputsConfig,
    ForecastInputsData,
)

ELEMENT_TYPE: Final = "solar"

CONF_CURTAILMENT: Final = "curtailment"
CONF_PRICE_PRODUCTION: Final = "price_production"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_PRODUCTION})


class SolarPricingConfig(TypedDict, total=False):
    """Pricing configuration for solar elements."""

    price_production: list[str] | str | float


class SolarPricingData(TypedDict, total=False):
    """Loaded pricing values for solar elements."""

    price_production: NDArray[np.floating[Any]] | float


class SolarAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for solar elements."""

    curtailment: str | bool


class SolarAdvancedData(TypedDict, total=False):
    """Loaded advanced values for solar elements."""

    curtailment: bool


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    """

    element_type: Literal["solar"]
    basic: BasicNameConnectionConfig
    inputs: ForecastInputsConfig
    pricing: SolarPricingConfig
    advanced: SolarAdvancedConfig


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values."""

    element_type: Literal["solar"]
    basic: BasicNameConnectionData
    inputs: ForecastInputsData
    pricing: SolarPricingData
    advanced: SolarAdvancedData


__all__ = [
    "CONF_CURTAILMENT",
    "CONF_FORECAST",
    "CONF_PRICE_PRODUCTION",
    "ELEMENT_TYPE",
    "OPTIONAL_INPUT_FIELDS",
    "SECTION_ADVANCED",
    "SECTION_BASIC",
    "SECTION_INPUTS",
    "SECTION_PRICING",
    "SolarAdvancedConfig",
    "SolarConfigData",
    "SolarConfigSchema",
    "SolarPricingConfig",
]
