"""Grid element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

ElementTypeName = Literal["grid"]
ELEMENT_TYPE: ElementTypeName = "grid"

# Configuration field names
CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_LIMIT: Final = "import_limit"
CONF_EXPORT_LIMIT: Final = "export_limit"
CONF_CONNECTION: Final = "connection"

# Default values for optional fields ($/kWh for prices, kW for limits)
DEFAULT_IMPORT_PRICE: Final[float] = 0.1
DEFAULT_EXPORT_PRICE: Final[float] = 0.01
DEFAULT_IMPORT_LIMIT: Final[float] = 30.0
DEFAULT_EXPORT_LIMIT: Final[float] = 30.0

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
        output_type=OutputType.PRICE,
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
        output_type=OutputType.PRICE,
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
        output_type=OutputType.POWER_LIMIT,
        time_series=True,
        direction="+",
        default=DEFAULT_IMPORT_LIMIT,
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
        output_type=OutputType.POWER_LIMIT,
        time_series=True,
        direction="-",
        default=DEFAULT_EXPORT_LIMIT,
    ),
)


class GridConfigSchema(TypedDict):
    """Grid element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - list[str]: Entity IDs when mode is ENTITY_LINK
    - float: Constant value when mode is CONSTANT
    - NotRequired: Field not present when mode is NONE
    """

    element_type: Literal["grid"]
    name: str
    connection: str  # Element name to connect to

    # Price fields: required (user must select an entity or enter a value)
    import_price: list[str] | float  # Entity IDs or constant $/kWh
    export_price: list[str] | float  # Entity IDs or constant $/kWh

    # Power limit fields (optional)
    import_limit: NotRequired[list[str] | float]  # Entity IDs or constant kW
    export_limit: NotRequired[list[str] | float]  # Entity IDs or constant kW


class GridConfigData(TypedDict):
    """Grid element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["grid"]
    name: str
    connection: str  # Element name to connect to
    import_price: list[float]  # Loaded price values per period ($/kWh)
    export_price: list[float]  # Loaded price values per period ($/kWh)

    # Optional fields - now time series
    import_limit: NotRequired[list[float]]  # Loaded values per period (kW)
    export_limit: NotRequired[list[float]]  # Loaded values per period (kW)
