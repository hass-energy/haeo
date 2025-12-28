"""Inverter element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "inverter"

# Configuration field names
CONF_CONNECTION: Final = "connection"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"
CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"
CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"

# Default values
DEFAULT_EFFICIENCY: Final = 100.0


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for power limit sensors.
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to
    max_power_dc_to_ac: list[str]  # Entity IDs for DC to AC power limit
    max_power_ac_to_dc: list[str]  # Entity IDs for AC to DC power limit

    # Optional fields
    efficiency_dc_to_ac: NotRequired[float]  # Percentage (0-100)
    efficiency_ac_to_dc: NotRequired[float]  # Percentage (0-100)


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to
    max_power_dc_to_ac: list[float]  # Loaded power limit per period (kW)
    max_power_ac_to_dc: list[float]  # Loaded power limit per period (kW)

    # Optional fields
    efficiency_dc_to_ac: NotRequired[float]  # Percentage (0-100)
    efficiency_ac_to_dc: NotRequired[float]  # Percentage (0-100)
