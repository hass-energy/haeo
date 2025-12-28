"""Load element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"
CONF_SHEDDABLE: Final = "sheddable"
CONF_VALUE_RUNNING: Final = "value_running"

# Default values for optional fields
DEFAULTS: Final[dict[str, bool]] = {
    CONF_SHEDDABLE: False,
}


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str]  # Entity IDs for power forecast sensors

    # Optional fields
    sheddable: NotRequired[bool]  # Whether load can be shed
    value_running: NotRequired[float]  # $/kWh value when load is running


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)

    # Optional fields
    sheddable: NotRequired[bool]  # Whether load can be shed
    value_running: NotRequired[float]  # $/kWh value when load is running
