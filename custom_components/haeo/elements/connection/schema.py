"""Connection element schema definitions."""

from typing import Final, Literal, NotRequired, TypedDict

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import PERCENTAGE, UnitOfPower

from custom_components.haeo.elements.input_fields import NumberInputFieldInfo

ELEMENT_TYPE: Final = "connection"

# Configuration field names
CONF_SOURCE: Final = "source"
CONF_TARGET: Final = "target"
CONF_MAX_POWER_SOURCE_TARGET: Final = "max_power_source_target"
CONF_MAX_POWER_TARGET_SOURCE: Final = "max_power_target_source"
CONF_EFFICIENCY_SOURCE_TARGET: Final = "efficiency_source_target"
CONF_EFFICIENCY_TARGET_SOURCE: Final = "efficiency_target_source"
CONF_PRICE_SOURCE_TARGET: Final = "price_source_target"
CONF_PRICE_TARGET_SOURCE: Final = "price_target_source"

# Input field definitions for creating input entities
INPUT_FIELDS: Final[tuple[NumberInputFieldInfo, ...]] = (
    NumberInputFieldInfo(
        field_name=CONF_MAX_POWER_SOURCE_TARGET,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_SOURCE_TARGET,
            translation_key=CONF_MAX_POWER_SOURCE_TARGET,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type="power_limit",
        time_series=True,
    ),
    NumberInputFieldInfo(
        field_name=CONF_MAX_POWER_TARGET_SOURCE,
        entity_description=NumberEntityDescription(
            key=CONF_MAX_POWER_TARGET_SOURCE,
            translation_key=CONF_MAX_POWER_TARGET_SOURCE,
            native_unit_of_measurement=UnitOfPower.KILO_WATT,
            device_class=NumberDeviceClass.POWER,
            native_min_value=0.0,
            native_max_value=1000.0,
            native_step=0.1,
        ),
        output_type="power_limit",
        time_series=True,
    ),
    NumberInputFieldInfo(
        field_name=CONF_EFFICIENCY_SOURCE_TARGET,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_SOURCE_TARGET,
            translation_key=CONF_EFFICIENCY_SOURCE_TARGET,
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type="soc",
        time_series=True,
    ),
    NumberInputFieldInfo(
        field_name=CONF_EFFICIENCY_TARGET_SOURCE,
        entity_description=NumberEntityDescription(
            key=CONF_EFFICIENCY_TARGET_SOURCE,
            translation_key=CONF_EFFICIENCY_TARGET_SOURCE,
            native_unit_of_measurement=PERCENTAGE,
            device_class=NumberDeviceClass.POWER_FACTOR,
            native_min_value=50.0,
            native_max_value=100.0,
            native_step=0.1,
        ),
        output_type="soc",
        time_series=True,
    ),
    NumberInputFieldInfo(
        field_name=CONF_PRICE_SOURCE_TARGET,
        entity_description=NumberEntityDescription(
            key=CONF_PRICE_SOURCE_TARGET,
            translation_key=CONF_PRICE_SOURCE_TARGET,
            native_min_value=-1.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type="price",
        direction="-",
        time_series=True,
    ),
    NumberInputFieldInfo(
        field_name=CONF_PRICE_TARGET_SOURCE,
        entity_description=NumberEntityDescription(
            key=CONF_PRICE_TARGET_SOURCE,
            translation_key=CONF_PRICE_TARGET_SOURCE,
            native_min_value=-1.0,
            native_max_value=10.0,
            native_step=0.001,
        ),
        output_type="price",
        direction="-",
        time_series=True,
    ),
)


class ConnectionConfigSchema(TypedDict):
    """Connection element configuration as stored in Home Assistant.

    Schema mode contains entity IDs for power and efficiency sensors.
    """

    element_type: Literal["connection"]
    name: str
    source: str  # Source element name
    target: str  # Target element name

    # Optional fields
    max_power_source_target: NotRequired[list[str]]  # Entity IDs for power limit
    max_power_target_source: NotRequired[list[str]]  # Entity IDs for power limit
    efficiency_source_target: NotRequired[list[str]]  # Entity IDs for efficiency
    efficiency_target_source: NotRequired[list[str]]  # Entity IDs for efficiency
    price_source_target: NotRequired[list[str]]  # Entity IDs for price
    price_target_source: NotRequired[list[str]]  # Entity IDs for price


class ConnectionConfigData(TypedDict):
    """Connection element configuration with loaded values.

    Data mode contains resolved sensor values for optimization.
    """

    element_type: Literal["connection"]
    name: str
    source: str  # Source element name
    target: str  # Target element name

    # Optional fields
    max_power_source_target: NotRequired[list[float]]  # Loaded power limit per period (kW)
    max_power_target_source: NotRequired[list[float]]  # Loaded power limit per period (kW)
    efficiency_source_target: NotRequired[list[float]]  # Loaded efficiency per period (%)
    efficiency_target_source: NotRequired[list[float]]  # Loaded efficiency per period (%)
    price_source_target: NotRequired[list[float]]  # Loaded price per period ($/kWh)
    price_target_source: NotRequired[list[float]]  # Loaded price per period ($/kWh)
