"""Energy storage element schema definitions.

This is an advanced element that provides direct access to the model layer EnergyStorage element.
Unlike the standard Battery element which creates multiple partitions and an internal node,
this element creates a single energy storage partition that must be connected manually via Connection.
"""

from typing import Final, Literal, TypedDict

ELEMENT_TYPE: Final = "energy_storage"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"


class EnergyStorageConfigSchema(TypedDict):
    """Energy storage element configuration as stored in Home Assistant.

    A single energy storage partition with capacity and initial charge. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["energy_storage"]
    name: str
    capacity: list[str]  # Energy sensor entity IDs
    initial_charge: list[str]  # Energy sensor entity IDs


class EnergyStorageConfigData(TypedDict):
    """Energy storage element configuration with loaded values."""

    element_type: Literal["energy_storage"]
    name: str
    capacity: list[float]  # kWh per period (uses first value)
    initial_charge: list[float]  # kWh per period (uses first value)
