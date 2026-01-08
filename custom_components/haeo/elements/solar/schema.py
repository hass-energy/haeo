"""Solar element schema definitions."""

from typing import Any, Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

ELEMENT_TYPE: Final = "solar"

# Configuration field names
CONF_FORECAST: Final = "forecast"
CONF_PRICE_PRODUCTION: Final = "price_production"
CONF_CURTAILMENT: Final = "curtailment"
CONF_CONNECTION: Final = "connection"

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
    ),
)


class SolarConfigSchema(TypedDict):
    """Solar element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - list[str]: Entity IDs when linking to sensors
    - float/bool: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["solar"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[str] | float  # Entity IDs or constant kW

    # Required fields
    curtailment: list[str] | bool  # Entity IDs or constant boolean

    # Optional fields
    price_production: NotRequired[list[str] | float]  # Entity IDs or constant $/kWh


class SolarConfigData(TypedDict):
    """Solar element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["solar"]
    name: str
    connection: str  # Element name to connect to
    forecast: list[float]  # Loaded power values per period (kW)
    curtailment: bool  # Whether solar can be curtailed
    price_production: float  # $/kWh production incentive (0.0 if not configured)
