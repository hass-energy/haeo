"""Grid element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    """

    element_type: Literal["grid"]
    name: str
    connection: str  # Element name to connect to
    import_price: list[str]  # Entity IDs for import price sensors
    export_price: list[str]  # Entity IDs for export price sensors

    # Optional fields
    import_limit: NotRequired[float]  # kW
    export_limit: NotRequired[float]  # kW


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["grid"]
    name: str
    connection: str  # Element name to connect to
    import_price: list[float]  # Loaded price values per period ($/kWh)
    export_price: list[float]  # Loaded price values per period ($/kWh)

    # Optional fields
    import_limit: NotRequired[float]  # kW
    export_limit: NotRequired[float]  # kW
