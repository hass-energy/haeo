"""Grid element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"
CONF_DEMAND_WINDOW_IMPORT: Final = "demand_window_import"
CONF_DEMAND_WINDOW_EXPORT: Final = "demand_window_export"
CONF_DEMAND_PRICE_IMPORT: Final = "demand_price_import"
CONF_DEMAND_PRICE_EXPORT: Final = "demand_price_export"
CONF_DEMAND_BLOCK_HOURS: Final = "demand_block_hours"
CONF_DEMAND_DAYS: Final = "demand_days"


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
    name: str
    connection: str  # Element name to connect to

    # Price fields: required (user must select an entity or enter a value)
    # Lists supported for chaining current + forecast sensors
    import_price: list[str] | str | float  # Entity ID(s) or constant $/kWh - list for chaining
    export_price: list[str] | str | float  # Entity ID(s) or constant $/kWh - list for chaining

    # Power limit fields (optional)
    import_limit: NotRequired[str | float]  # Entity ID or constant kW
    export_limit: NotRequired[str | float]  # Entity ID or constant kW
    demand_window_import: NotRequired[str | float]  # Entity ID or constant weight (0-1)
    demand_window_export: NotRequired[str | float]  # Entity ID or constant weight (0-1)
    demand_price_import: NotRequired[str | float]  # Entity ID or constant $/kW/day
    demand_price_export: NotRequired[str | float]  # Entity ID or constant $/kW/day
    demand_block_hours: NotRequired[str | float]  # Entity ID or constant hours
    demand_days: NotRequired[str | float]  # Entity ID or constant days


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["grid"]
    name: str
    connection: str  # Element name to connect to
    import_price: NDArray[np.floating[Any]] | float  # Loaded price values per period ($/kWh)
    export_price: NDArray[np.floating[Any]] | float  # Loaded price values per period ($/kWh)

    # Optional fields - now time series
    import_limit: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded values per period (kW)
    export_limit: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded values per period (kW)
    demand_window_import: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded demand window weights (0-1)
    demand_window_export: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded demand window weights (0-1)
    demand_price_import: NotRequired[float]  # Demand price in $/kW/day
    demand_price_export: NotRequired[float]  # Demand price in $/kW/day
    demand_block_hours: NotRequired[float]  # Demand block duration in hours
    demand_days: NotRequired[float]  # Demand billing days
