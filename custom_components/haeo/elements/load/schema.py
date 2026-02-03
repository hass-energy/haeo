"""Load element schema definitions."""

from typing import Any, Final, Literal, TypedDict

import numpy as np
from numpy.typing import NDArray

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"
CONF_SECTION_BASIC: Final = "basic"
CONF_SECTION_INPUTS: Final = "inputs"

OPTIONAL_INPUT_FIELDS: Final[frozenset[str]] = frozenset()


class LoadBasicConfig(TypedDict):
    """Basic configuration for load elements."""

    name: str
    connection: str  # Element name to connect to


class LoadInputsConfig(TypedDict):
    """Input configuration for load elements."""

    forecast: list[str] | str | float  # Entity ID(s) or constant kW - list for chaining


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors or constant values.
    """

    element_type: Literal["load"]
    basic: LoadBasicConfig
    inputs: LoadInputsConfig


class LoadBasicData(TypedDict):
    """Loaded basic values for load elements."""

    name: str
    connection: str  # Element name to connect to


class LoadInputsData(TypedDict):
    """Loaded input values for load elements."""

    forecast: NDArray[np.floating[Any]] | float  # Loaded power values per period (kW)


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["load"]
    basic: LoadBasicData
    inputs: LoadInputsData
