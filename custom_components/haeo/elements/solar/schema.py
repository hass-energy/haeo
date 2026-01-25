"""Solar element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_ADVANCED: Final = "advanced"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_CURTAILMENT, CONF_PRICE_PRODUCTION})


class SolarBasicConfig(TypedDict):
    """Basic configuration for solar elements."""

    name: str
    connection: str  # Element name to connect to
    forecast: list[str] | str | float  # Entity ID(s) or constant kW - list for chaining


class SolarAdvancedConfig(TypedDict, total=False):
    """Advanced configuration for solar elements."""

    curtailment: str | bool  # Entity ID or constant boolean (default: True)
    price_production: list[str] | str | float  # Entity ID(s) or constant $/kWh


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - list[str]: Entity IDs for chained forecasts
    - str: Single entity ID
    - float/bool: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["solar"]
    basic: SolarBasicConfig
    advanced: SolarAdvancedConfig


class SolarBasicData(TypedDict):
    """Loaded basic values for solar elements."""

    name: str
    connection: str  # Element name to connect to
    forecast: NDArray[np.floating[Any]] | float  # Loaded power values per period (kW)


class SolarAdvancedData(TypedDict, total=False):
    """Loaded advanced values for solar elements."""

    curtailment: bool  # Whether solar can be curtailed (default: True)
    price_production: NDArray[np.floating[Any]] | float  # $/kWh production incentive (default: 0.0)


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["solar"]
    basic: SolarBasicData
    advanced: SolarAdvancedData
