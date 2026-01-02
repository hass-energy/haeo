"""Battery section element schema definitions.

This is an advanced element that provides direct access to the model layer Battery element.
Unlike the standard Battery element which creates multiple sections and an internal node,
this element creates a single battery section that must be connected manually via Connection.
"""

from typing import Final, Literal, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfEnergy

from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType

ELEMENT_TYPE: Final = "battery_section"

# Configuration field names
CONF_CAPACITY: Final = "capacity"
CONF_INITIAL_CHARGE: Final = "initial_charge"


# Input fields for entity selection
INPUT_FIELDS: Final[tuple[InputFieldInfo[NumberEntityDescription], ...]] = (
    InputFieldInfo(
        field_name=CONF_CAPACITY,
        entity_description=NumberEntityDescription(
            key=CONF_CAPACITY,
            translation_key=f"{ELEMENT_TYPE}_{CONF_CAPACITY}",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=NumberDeviceClass.ENERGY_STORAGE,
            native_min_value=0.1,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.ENERGY,
        time_series=False,
        default=None,
    ),
    InputFieldInfo(
        field_name=CONF_INITIAL_CHARGE,
        entity_description=NumberEntityDescription(
            key=CONF_INITIAL_CHARGE,
            translation_key=f"{ELEMENT_TYPE}_{CONF_INITIAL_CHARGE}",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=NumberDeviceClass.ENERGY_STORAGE,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type=OutputType.ENERGY,
        time_series=False,
        default=None,
    ),
)


class BatterySectionConfigSchema(TypedDict):
    """Battery section element configuration as stored in Home Assistant.

    A single battery section with capacity and initial charge. Unlike the standard Battery
    element, this does not create an internal node or implicit connections.
    Connect to other elements using explicit Connection elements.
    """

    element_type: Literal["battery_section"]
    name: str
    capacity: list[str]  # Energy sensor entity IDs
    initial_charge: list[str]  # Energy sensor entity IDs


class BatterySectionConfigData(TypedDict):
    """Battery section element configuration with loaded values."""

    element_type: Literal["battery_section"]
    name: str
    capacity: list[float]  # kWh per period (uses first value)
    initial_charge: list[float]  # kWh per period (uses first value)
