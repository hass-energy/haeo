"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Final, Literal, TypedDict

ELEMENT_TYPE: Final = "battery_section"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant.

    A single battery section with capacity and initial charge. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["battery_section"]
    name: str
    capacity: list[str]  # Energy sensor entity IDs
    initial_charge: list[str]  # Energy sensor entity IDs


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    name: str
    capacity: list[float]  # kWh per period (uses first value)
    initial_charge: list[float]  # kWh per period (uses first value)
