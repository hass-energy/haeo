"""Input field metadata for creating input entities.

Defines which config fields should become input entities (NumberEntity/SwitchEntity)
and their associated metadata like units, limits, and device classes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower


class InputEntityType(Enum):
    """Type of input entity to create."""

    NUMBER = "number"
    SWITCH = "switch"


@dataclass(frozen=True, slots=True)
class InputFieldInfo:
    """Metadata for a config field that becomes an input entity.

    Attributes:
        field_name: The key in the element's ConfigSchema
        entity_type: Whether this becomes a NumberEntity or SwitchEntity
        output_type: From model.const OUTPUT_TYPE_* for categorization
        unit: Native unit of measurement
        min_value: Minimum allowed value (for numbers)
        max_value: Maximum allowed value (for numbers)
        step: Step size for UI (for numbers)
        device_class: Home Assistant device class
        translation_key: Override translation key if different from field_name
        direction: "+" or "-" for power direction attributes
        time_series: Whether this field is time series (list) or scalar

    """

    field_name: str
    entity_type: InputEntityType
    output_type: str
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    device_class: NumberDeviceClass | None = None
    translation_key: str | None = None
    direction: str | None = None
    time_series: bool = False


# Field definitions per element type
# Each list contains InputFieldInfo for fields that should become input entities

BATTERY_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="capacity",
        entity_type=InputEntityType.NUMBER,
        output_type="energy",
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        min_value=0.1,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.ENERGY_STORAGE,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="initial_charge_percentage",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.BATTERY,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="min_charge_percentage",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name="max_charge_percentage",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name="efficiency",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
    ),
    InputFieldInfo(
        field_name="max_charge_power",
        entity_type=InputEntityType.NUMBER,
        output_type="power",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="+",
        time_series=True,
    ),
    InputFieldInfo(
        field_name="max_discharge_power",
        entity_type=InputEntityType.NUMBER,
        output_type="power",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        direction="-",
        time_series=True,
    ),
    InputFieldInfo(
        field_name="early_charge_incentive",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh, set at runtime
        min_value=0.0,
        max_value=1.0,
        step=0.001,
    ),
    InputFieldInfo(
        field_name="discharge_cost",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh, set at runtime
        min_value=0.0,
        max_value=1.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="undercharge_percentage",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name="overcharge_percentage",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=0.0,
        max_value=100.0,
        step=1.0,
        device_class=NumberDeviceClass.BATTERY,
    ),
    InputFieldInfo(
        field_name="undercharge_cost",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="overcharge_cost",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=0.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
)

GRID_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="import_price",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="export_price",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="import_limit",
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
        field_name="export_limit",
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

SOLAR_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="forecast",
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
        field_name="price_production",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,  # Currency per kWh
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
    ),
    InputFieldInfo(
        field_name="curtailment",
        entity_type=InputEntityType.SWITCH,
        output_type="status",
    ),
)

LOAD_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="forecast",
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

INVERTER_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="max_power_dc_to_ac",
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="max_power_ac_to_dc",
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="efficiency_dc_to_ac",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",  # Using soc type for efficiency percentages
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
    ),
    InputFieldInfo(
        field_name="efficiency_ac_to_dc",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
    ),
)

CONNECTION_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="max_power_source_target",
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="max_power_target_source",
        entity_type=InputEntityType.NUMBER,
        output_type="power_limit",
        unit=UnitOfPower.KILO_WATT,
        min_value=0.0,
        max_value=1000.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="efficiency_source_target",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="efficiency_target_source",
        entity_type=InputEntityType.NUMBER,
        output_type="soc",
        unit=PERCENTAGE,
        min_value=50.0,
        max_value=100.0,
        step=0.1,
        device_class=NumberDeviceClass.POWER_FACTOR,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="price_source_target",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
    InputFieldInfo(
        field_name="price_target_source",
        entity_type=InputEntityType.NUMBER,
        output_type="price",
        unit=None,
        min_value=-1.0,
        max_value=10.0,
        step=0.001,
        time_series=True,
    ),
)

NODE_INPUT_FIELDS: Final[tuple[InputFieldInfo, ...]] = (
    InputFieldInfo(
        field_name="is_source",
        entity_type=InputEntityType.SWITCH,
        output_type="status",
    ),
    InputFieldInfo(
        field_name="is_sink",
        entity_type=InputEntityType.SWITCH,
        output_type="status",
    ),
)


# Registry mapping element types to their input field definitions
_INPUT_FIELDS_REGISTRY: Final[dict[str, tuple[InputFieldInfo, ...]]] = {
    "battery": BATTERY_INPUT_FIELDS,
    "grid": GRID_INPUT_FIELDS,
    "solar": SOLAR_INPUT_FIELDS,
    "load": LOAD_INPUT_FIELDS,
    "inverter": INVERTER_INPUT_FIELDS,
    "connection": CONNECTION_INPUT_FIELDS,
    "node": NODE_INPUT_FIELDS,
}


def get_input_fields(element_type: str) -> tuple[InputFieldInfo, ...]:
    """Return input field definitions for an element type.

    Args:
        element_type: The element type (e.g., "battery", "grid")

    Returns:
        Tuple of InputFieldInfo for fields that should become input entities.
        Returns empty tuple for unknown element types.

    """
    return _INPUT_FIELDS_REGISTRY.get(element_type, ())
