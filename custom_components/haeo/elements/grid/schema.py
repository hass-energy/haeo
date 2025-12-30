"""Grid element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo

ELEMENT_TYPE: Final = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_IMPORT_PRICE,
        entity_description=NumberEntityDescription(
            key=CONF_IMPORT_PRICE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_IMPORT_PRICE}",
            native_min_value=-1.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type="price",
        time_series=True,
        direction="-",  # Import = consuming from grid = cost
    ),
    InputFieldInfo(
        field_name=CONF_EXPORT_PRICE,
        entity_description=NumberEntityDescription(
            key=CONF_EXPORT_PRICE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EXPORT_PRICE}",
            native_min_value=-1.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type="price",
        time_series=True,
        direction="+",  # Export = producing to grid = revenue
    ),
    InputFieldInfo(
        field_name=CONF_IMPORT_LIMIT,
        entity_description=NumberEntityDescription(
            key=CONF_IMPORT_LIMIT,
            translation_key=f"{ELEMENT_TYPE}_{CONF_IMPORT_LIMIT}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type="power_limit",
        direction="+",
    ),
    InputFieldInfo(
        field_name=CONF_EXPORT_LIMIT,
        entity_description=NumberEntityDescription(
            key=CONF_EXPORT_LIMIT,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EXPORT_LIMIT}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type="power_limit",
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
