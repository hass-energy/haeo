"""Load element schema definitions."""

from typing import Final, Literal, TypedDict

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputEntityType, InputFieldInfo

ELEMENT_TYPE: Final = "load"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_CONNECTION: Final = "connection"

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name=CONF_FORECAST,
        entity_type=InputEntityType.NUMBER,
        output_type="power",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.01,
        device_class=NumberDeviceClass.POWER,
        direction="+",
        time_series=True,
    ),
)


class LoadConfigSchema(TypedDict):
    """Load element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for forecast sensors.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str]  # Entity IDs for power forecast sensors


class LoadConfigData(TypedDict):
    """Load element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["load"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)
