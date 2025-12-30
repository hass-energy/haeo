"""Grid element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputEntityType, InputFieldInfo

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name=CONF_IMPORT_PRICE,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
        direction="-",  # Import = consuming from grid = cost
    ),
    InputFieldInfo(
        field_name=CONF_EXPORT_PRICE,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
        direction="+",  # Export = producing to grid = revenue
    ),
    InputFieldInfo(
        field_name=CONF_IMPORT_LIMIT,
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="+",
    ),
    InputFieldInfo(
        field_name=CONF_EXPORT_LIMIT,
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="-",
    ),
)


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
