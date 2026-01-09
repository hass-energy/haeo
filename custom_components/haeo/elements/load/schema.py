"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

ElementTypeName = Literal["load"]
ELEMENT_TYPE: ElementTypeName = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"

# Default value for empty forecast (kW)
DEFAULT_FORECAST: Final[float] = 0.0

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_FORECAST,
        entity_description=NumberEntityDescription(
            key=CONF_FORECAST,
            translation_key=f"{ELEMENT_TYPE}_{CONF_FORECAST}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.01,
        ),
        output_type=OutputType.POWER,
        direction="+",
        time_series=True,
        default=DEFAULT_FORECAST,
    ),
)


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors or constant values.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str] | float  # Entity IDs for power forecast sensors or constant value (kW)


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)
