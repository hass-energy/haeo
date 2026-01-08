"""Inverter element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfPower

from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model.const import OutputType

ELEMENT_TYPE: Final = "inverter"

# Configuration field names
CONF_CONNECTION: Final = "connection"
CONF_EFFICIENCY_DC_TO_AC: Final = "efficiency_dc_to_ac"
CONF_EFFICIENCY_AC_TO_DC: Final = "efficiency_ac_to_dc"
CONF_MAX_POWER_DC_TO_AC: Final = "max_power_dc_to_ac"
CONF_MAX_POWER_AC_TO_DC: Final = "max_power_ac_to_dc"

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_MAX_POWER_DC_TO_AC,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_DC_TO_AC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_DC_TO_AC}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER_LIMIT,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_MAX_POWER_AC_TO_DC,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_AC_TO_DC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_AC_TO_DC}",
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.POWER_LIMIT,
        time_series=True,
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY_DC_TO_AC,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_DC_TO_AC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_DC_TO_AC}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        defaults=InputFieldDefaults(mode="value", value=100.0),
    ),
    InputFieldInfo(
        field_name=CONF_EFFICIENCY_AC_TO_DC,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_AC_TO_DC,
            translation_key=f"{ELEMENT_TYPE}_{CONF_EFFICIENCY_AC_TO_DC}",
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type=OutputType.EFFICIENCY,
        defaults=InputFieldDefaults(mode="value", value=100.0),
    ),
)


class InverterConfigSchema(TypedDict):
    """Inverter element configuration as stored in Home Assistant.

    Schema mode contains entity IDs and constant values from the config flow.
    Values can be:
    - list[str]: Entity IDs when linking to sensors
    - float: Constant value when using HAEO Configurable
    - NotRequired: Field not present when using default
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to

    # Power limit fields: required (user must select an entity or enter a value)
    max_power_dc_to_ac: list[str] | float  # Entity IDs or constant kW
    max_power_ac_to_dc: list[str] | float  # Entity IDs or constant kW

    # Efficiency fields (optional)
    efficiency_dc_to_ac: NotRequired[list[str] | float]  # Entity IDs or constant %
    efficiency_ac_to_dc: NotRequired[list[str] | float]  # Entity IDs or constant %


class InverterConfigData(TypedDict):
    """Inverter element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["inverter"]
    name: str
    connection: str  # AC side node to connect to
    max_power_dc_to_ac: list[float]  # Loaded power limit per period (kW)
    max_power_ac_to_dc: list[float]  # Loaded power limit per period (kW)
    efficiency_dc_to_ac: float  # Percentage (0-100), defaults to 100% (no loss)
    efficiency_ac_to_dc: float  # Percentage (0-100), defaults to 100% (no loss)
