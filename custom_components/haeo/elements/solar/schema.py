"""Solar element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"


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
    name: str
    connection: str  # Element name to connect to
    forecast: list[str] | str | float  # Entity ID(s) or constant kW - list for chaining

    # Optional fields (with sensible defaults)
    curtailment: NotRequired[str | bool]  # Entity ID or constant boolean (default: True)
    price_production: NotRequired[list[str] | str | float]  # Entity ID(s) or constant $/kWh


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["solar"]
    name: str
    connection: str  # Element name to connect to
    forecast: NDArray[np.floating[Any]]  # Loaded power values per period (kW)
    curtailment: NotRequired[bool]  # Whether solar can be curtailed (default: True)
    price_production: NotRequired[NDArray[np.floating[Any]]]  # $/kWh production incentive (default: 0.0)
