"""Solar element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

ElementTypeName = Literal["solar"]
ELEMENT_TYPE: ElementTypeName = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

# Default values for optional fields
DEFAULTS: Final[dict[str, bool]] = {
    CONF_CURTAILMENT: True,
}

# Input field definitions for creating input entities (mix of Number and Switch)
INPUT_FIELDS: Final[tuple[InputFieldInfo[Any], ...]] = (
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
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_PRICE_PRODUCTION,
        entity_description=NumberEntityDescription(
            key=CONF_PRICE_PRODUCTION,
            translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_PRODUCTION}",
            native_min_value=-1.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type=OutputType.PRICE,
        direction="+",
    ),
    InputFieldInfo(
        field_name=CONF_CURTAILMENT,
        entity_description=SwitchEntityDescription(
            key=CONF_CURTAILMENT,
            translation_key=f"{ELEMENT_TYPE}_{CONF_CURTAILMENT}",
        ),
        output_type=OutputType.STATUS,
        default=True,
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
