"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "battery_section"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_INPUTS: Final = "inputs"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class BatterySectionBasicConfig(TypedDict):
    """Basic configuration for battery sections."""

    name: str


class BatterySectionInputsConfig(TypedDict):
    """Input configuration for battery sections."""

    capacity: str | float  # Entity ID or constant kWh
    initial_charge: str | float  # Entity ID or constant kWh


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - str: Entity ID when linking to a sensor
    - float: Constant value when using HAEO Configurable

    A single battery section with capacity and initial charge. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["battery_section"]
    basic: BatterySectionBasicConfig
    inputs: BatterySectionInputsConfig


class BatterySectionBasicData(TypedDict):
    """Loaded basic values for battery sections."""

    name: str


class BatterySectionInputsData(TypedDict):
    """Loaded input values for battery sections."""

    capacity: NDArray[np.floating[Any]]  # kWh at each time boundary (n+1 values)
    initial_charge: NDArray[np.floating[Any]]  # kWh per period (uses first value)


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    basic: BatterySectionBasicData
    inputs: BatterySectionInputsData
