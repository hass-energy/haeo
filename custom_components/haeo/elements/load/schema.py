"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors or constant values.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str] | str | float  # Entity ID(s) or constant kW - list for chaining


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)
