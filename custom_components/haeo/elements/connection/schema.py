"""Connection element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "connection"

# Configuration field names
CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"
CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"
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


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - str: Entity ID when linking to a sensor
    - float: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["connection"]
    name: str
    source: str  # Source element name
    target: str  # Target element name

    # Optional fields
    max_power_source_target: NotRequired[str | float]  # Entity ID or constant kW
    max_power_target_source: NotRequired[str | float]  # Entity ID or constant kW
    efficiency_source_target: NotRequired[str | float]  # Entity ID or constant %
    efficiency_target_source: NotRequired[str | float]  # Entity ID or constant %
    price_source_target: NotRequired[str | float]  # Entity ID or constant $/kWh
    price_target_source: NotRequired[str | float]  # Entity ID or constant $/kWh
    demand_window_source_target: NotRequired[str | float]  # Entity ID or constant weight (0-1)
    demand_window_target_source: NotRequired[str | float]  # Entity ID or constant weight (0-1)
    demand_price_source_target: NotRequired[str | float]  # Entity ID or constant $/kW/day
    demand_price_target_source: NotRequired[str | float]  # Entity ID or constant $/kW/day
    demand_current_energy_source_target: NotRequired[str | float]  # Entity ID or constant kWh
    demand_current_energy_target_source: NotRequired[str | float]  # Entity ID or constant kWh
    demand_block_hours: NotRequired[str | float]  # Entity ID or constant hours
    demand_days: NotRequired[str | float]  # Entity ID or constant days


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["connection"]
    name: str
    source: str  # Source element name
    target: str  # Target element name

    # Optional fields
    max_power_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded power limit per period (kW)
    max_power_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded power limit per period (kW)
    efficiency_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded efficiency ratio per period (0-1)
    efficiency_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded efficiency ratio per period (0-1)
    price_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded price per period ($/kWh)
    price_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded price per period ($/kWh)
    demand_window_source_target: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded demand window weights (0-1)
    demand_window_target_source: NotRequired[NDArray[np.floating[Any]] | float]  # Loaded demand window weights (0-1)
    demand_price_source_target: NotRequired[float]  # Demand price in $/kW/day
    demand_price_target_source: NotRequired[float]  # Demand price in $/kW/day
    demand_current_energy_source_target: NotRequired[float]  # Demand energy already used (kWh)
    demand_current_energy_target_source: NotRequired[float]  # Demand energy already used (kWh)
    demand_block_hours: NotRequired[float]  # Demand block duration in hours
    demand_days: NotRequired[float]  # Demand billing days
