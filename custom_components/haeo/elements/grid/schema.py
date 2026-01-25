"""Grid element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_LIMITS: Final = "limits"
CONF_SECTION_PRICING: Final = "pricing"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset({CONF_IMPORT_LIMIT, CONF_EXPORT_LIMIT})


class GridBasicConfig(TypedDict):
    """Required basic configuration for grid elements."""

    name: str
    connection: str  # Element name to connect to


class GridPricingConfig(TypedDict):
    """Pricing configuration for grid elements."""

    # Price fields: required (user must select an entity or enter a value)
    # Lists supported for chaining current + forecast sensors
    import_price: list[str] | str | float  # Entity ID(s) or constant $/kWh - list for chaining
    export_price: list[str] | str | float  # Entity ID(s) or constant $/kWh - list for chaining


class GridLimitsConfig(TypedDict, total=False):
    """Optional limits configuration for grid elements."""

    import_limit: str | float  # Entity ID or constant kW
    export_limit: str | float  # Entity ID or constant kW


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - list[str]: Entity IDs for chained price forecasts
    - str: Single entity ID
    - float: Constant value when mode is CONSTANT
    - NotRequired: Field not present when mode is NONE
    """

    element_type: Literal["grid"]
    basic: GridBasicConfig
    pricing: GridPricingConfig
    limits: GridLimitsConfig


class GridBasicData(TypedDict):
    """Loaded basic values for grid elements."""

    name: str
    connection: str  # Element name to connect to


class GridPricingData(TypedDict):
    """Loaded pricing values for grid elements."""

    import_price: NDArray[np.floating[Any]] | float  # Loaded price values per period ($/kWh)
    export_price: NDArray[np.floating[Any]] | float  # Loaded price values per period ($/kWh)


class GridLimitsData(TypedDict, total=False):
    """Loaded limit values for grid elements."""

    import_limit: NDArray[np.floating[Any]] | float  # Loaded values per period (kW)
    export_limit: NDArray[np.floating[Any]] | float  # Loaded values per period (kW)


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["grid"]
    basic: GridBasicData
    pricing: GridPricingData
    limits: GridLimitsData
