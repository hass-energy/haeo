"""Inverter element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "inverter"

# Configuration field names
CONF_CONNECTION: Final = "connection"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"
CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"
CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - str: Entity ID when linking to a sensor
    - float: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to

    # Power limit fields: required (user must select an entity or enter a value)
    max_power_dc_to_ac: str | float  # Entity ID or constant kW
    max_power_ac_to_dc: str | float  # Entity ID or constant kW

    # Efficiency fields (optional)
    efficiency_dc_to_ac: NotRequired[str | float]  # Entity ID or constant %
    efficiency_ac_to_dc: NotRequired[str | float]  # Entity ID or constant %


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to
    max_power_dc_to_ac: list[float]  # Loaded power limit per period (kW)
    max_power_ac_to_dc: list[float]  # Loaded power limit per period (kW)
    efficiency_dc_to_ac: NotRequired[float]  # Percentage (0-100), defaults to 100% (no loss)
    efficiency_ac_to_dc: NotRequired[float]  # Percentage (0-100), defaults to 100% (no loss)
