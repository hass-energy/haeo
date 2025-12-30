"""Solar element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputEntityType, InputFieldInfo

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

# Default values for optional fields
DEFAULTS: Final[dict[str, bool]] = {
    CONF_CURTAILMENT: True,
}

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
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_PRICE_PRODUCTION,
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        direction="+",
    ),
    InputFieldInfo(
        field_name=CONF_CURTAILMENT,
        entity_type=InputEntityType.SWITCH,
        output_type="status",
    ),
)


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
