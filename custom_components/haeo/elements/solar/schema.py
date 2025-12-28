"""Solar element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

# Default values
DEFAULT_CURTAILMENT: Final = True


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors.
    """

    element_type: Literal["solar"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str]  # Entity IDs for power forecast sensors

    # Optional fields
    price_production: NotRequired[float]  # $/kWh production incentive
    curtailment: NotRequired[bool]  # Whether solar can be curtailed


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["solar"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)

    # Optional fields
    price_production: NotRequired[float]  # $/kWh production incentive
    curtailment: NotRequired[bool]  # Whether solar can be curtailed
