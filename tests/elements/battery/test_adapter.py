"""Tests for battery adapter config handling and model elements."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.elements import battery
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements import ModelElementConfig
from custom_components.haeo.model.elements.connection import ConnectionElementConfig
from custom_components.haeo.model.elements.segments import is_efficiency_spec
from custom_components.haeo.schema import (
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
)


def _get_connection(elements: Sequence[ModelElementConfig], name: str) -> ConnectionElementConfig:
    """Extract connection element by name from model elements list."""
    connection = next(
        (e for e in elements if e.get("element_type") == MODEL_ELEMENT_TYPE_CONNECTION and e.get("name") == name),
        None,
    )
    if connection is None:
        msg = f"Connection '{name}' not found in elements"
        raise ValueError(msg)
    return connection  # type: ignore[return-value]


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


def _wrap_config(flat: dict[str, object]) -> battery.BatteryConfigSchema:
    """Wrap flat battery config values into sectioned config."""

    def to_schema_value(value: object) -> object:
        if value is None:
            return as_none_value()
        if isinstance(value, bool):
            return as_constant_value(value)
        if isinstance(value, (int, float)):
            return as_constant_value(float(value))
        if isinstance(value, str):
            return as_entity_value([value])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            if not value:
                return as_none_value()
            return as_entity_value(value)
        return value

    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}
    partitioning: dict[str, object] = {}
    undercharge: dict[str, object] = {}
    overcharge: dict[str, object] = {}

    for key, value in flat.items():
        if key in (
            "name",
            "connection",
        ):
            if key == "connection" and isinstance(value, str):
                common[key] = as_connection_target(value)
            else:
                common[key] = value
        elif key in (
            "capacity",
            "initial_charge_percentage",
        ):
            storage[key] = to_schema_value(value)
        elif key in (
            "min_charge_percentage",
            "max_charge_percentage",
        ):
            limits[key] = to_schema_value(value)
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = to_schema_value(value)
        elif key == "configure_partitions":
            partitioning[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = to_schema_value(value)
        elif key in (
            "price_source_target",
            "price_target_source",
            "salvage_value",
        ):
            pricing[key] = to_schema_value(value)
        elif key == "undercharge" and isinstance(value, dict):
            undercharge.update({subkey: to_schema_value(subvalue) for subkey, subvalue in value.items()})
        elif key == "overcharge" and isinstance(value, dict):
            overcharge.update({subkey: to_schema_value(subvalue) for subkey, subvalue in value.items()})

    pricing.setdefault("salvage_value", as_constant_value(0.0))

    config: dict[str, object] = {
        "element_type": "battery",
        battery.SECTION_COMMON: common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_LIMITS: limits,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
        battery.SECTION_PARTITIONING: partitioning,
        battery.SECTION_UNDERCHARGE: undercharge,
        battery.SECTION_OVERCHARGE: overcharge,
    }
    return config  # type: ignore[return-value]


def _wrap_data(flat: dict[str, object]) -> battery.BatteryConfigData:
    """Wrap flat battery config data values into sectioned config data."""
    common: dict[str, object] = {}
    storage: dict[str, object] = {}
    limits: dict[str, object] = {}
    power_limits: dict[str, object] = {}
    pricing: dict[str, object] = {}
    efficiency: dict[str, object] = {}
    partitioning: dict[str, object] = {}
    undercharge: dict[str, object] = {}
    overcharge: dict[str, object] = {}

    for key, value in flat.items():
        if key in (
            "name",
            "connection",
        ):
            if key == "connection" and isinstance(value, str):
                common[key] = as_connection_target(value)
            else:
                common[key] = value
        elif key in (
            "capacity",
            "initial_charge_percentage",
        ):
            storage[key] = value
        elif key in (
            "min_charge_percentage",
            "max_charge_percentage",
        ):
            limits[key] = value
        elif key in ("efficiency_source_target", "efficiency_target_source"):
            efficiency[key] = value
        elif key == "configure_partitions":
            partitioning[key] = value
        elif key in (
            "max_power_source_target",
            "max_power_target_source",
        ):
            power_limits[key] = value
        elif key in (
            "price_source_target",
            "price_target_source",
            "salvage_value",
        ):
            pricing[key] = value
        elif key == "undercharge" and isinstance(value, dict):
            undercharge.update(value)
        elif key == "overcharge" and isinstance(value, dict):
            overcharge.update(value)

    pricing.setdefault(battery.CONF_SALVAGE_VALUE, 0.0)

    config: dict[str, object] = {
        "element_type": "battery",
        battery.SECTION_COMMON: common,
        battery.SECTION_STORAGE: storage,
        battery.SECTION_LIMITS: limits,
        battery.SECTION_POWER_LIMITS: power_limits,
        battery.SECTION_PRICING: pricing,
        battery.SECTION_EFFICIENCY: efficiency,
        battery.SECTION_PARTITIONING: partitioning,
        battery.SECTION_UNDERCHARGE: undercharge,
        battery.SECTION_OVERCHARGE: overcharge,
    }
    return config  # type: ignore[return-value]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.max_discharge",
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_required_power_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required power sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    # max_power_source_target sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.missing",
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_capacity_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when capacity sensor is missing."""
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    # capacity sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.missing_capacity",
            "initial_charge_percentage": "sensor.initial",
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_required_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")
    # initial_charge_percentage sensor is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.missing",
            "max_power_target_source": "sensor.max_charge",
            "max_power_source_target": "sensor.max_discharge",
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_with_list_entity_ids_all_exist(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] entity IDs all exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.price_source_target_1", "0.05", "$/kWh")
    _set_sensor(hass, "sensor.price_source_target_2", "0.06", "$/kWh")

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            # List of entity IDs for chained forecasts
            "price_source_target": ["sensor.price_source_target_1", "sensor.price_source_target_2"],
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is True


async def test_available_with_list_entity_ids_one_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when list[str] entity ID has one missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.price_source_target_1", "0.05", "$/kWh")
    # sensor.price_source_target_2 is missing

    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            # List of entity IDs where one is missing
            "price_source_target": ["sensor.price_source_target_1", "sensor.missing"],
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is False


async def test_available_with_empty_list_returns_true(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] is empty."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    # This tests the `if value else True` branch for empty lists
    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": "sensor.capacity",
            "initial_charge_percentage": "sensor.initial",
            "price_source_target": [],  # Empty list
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is True


async def test_available_returns_true_with_constant_values(hass: HomeAssistant) -> None:
    """Battery available() returns True when values are constants."""
    config: battery.BatteryConfigSchema = _wrap_config(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": 10.0,
            "initial_charge_percentage": 0.5,
            "max_power_target_source": 5.0,
            "max_power_source_target": 4.0,
            "price_source_target": 0.15,
            "price_target_source": 0.05,
            "efficiency_source_target": 0.95,
            "efficiency_target_source": 0.94,
            "undercharge": {"partition_percentage": 0.1, "partition_cost": 0.2},
            "overcharge": {"partition_percentage": 0.05, "partition_cost": 0.15},
        }
    )

    result = schema_config_available(config, hass=hass)
    assert result is True


def test_model_elements_omits_efficiency_when_missing() -> None:
    """model_elements() should leave efficiency to model defaults when missing."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
        }
    )

    elements = battery.adapter.model_elements(config_data)

    battery_element = next(element for element in elements if element["element_type"] == MODEL_ELEMENT_TYPE_BATTERY and element["name"] == "test_battery")
    np.testing.assert_array_equal(battery_element["capacity"], [10.0, 10.0, 10.0])

    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    assert efficiency_segment.get("efficiency_source_target") is None
    assert efficiency_segment.get("efficiency_target_source") is None


def test_model_elements_passes_efficiency_when_present() -> None:
    """model_elements() should pass through provided efficiency values."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
            "efficiency_source_target": np.array([0.95, 0.95]),
            "efficiency_target_source": np.array([0.95, 0.95]),
        }
    )

    elements = battery.adapter.model_elements(config_data)

    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    efficiency_source_target = efficiency_segment.get("efficiency_source_target")
    assert efficiency_source_target is not None
    np.testing.assert_array_equal(efficiency_source_target, [0.95, 0.95])
    efficiency_target_source = efficiency_segment.get("efficiency_target_source")
    assert efficiency_target_source is not None
    np.testing.assert_array_equal(efficiency_target_source, [0.95, 0.95])


def test_model_elements_overcharge_only_adds_soc_pricing() -> None:
    """SOC pricing is added when only overcharge inputs are configured."""
    config_data: battery.BatteryConfigData = _wrap_data(
        {
            "name": "test_battery",
            "connection": "main_bus",
            "capacity": np.array([10.0, 10.0, 10.0]),
            "initial_charge_percentage": 0.5,
            "min_charge_percentage": np.array([0.1, 0.1, 0.1]),
            "max_charge_percentage": np.array([0.9, 0.9, 0.9]),
            "overcharge": {
                "percentage": np.array([0.95, 0.95, 0.95]),
                "cost": np.array([0.2, 0.2]),
            },
        }
    )

    elements = battery.adapter.model_elements(config_data)
    connection = _get_connection(elements, "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    soc_pricing = segments.get("soc_pricing")
    assert soc_pricing is not None
    assert soc_pricing.get("discharge_energy_threshold") is None
    assert soc_pricing.get("charge_capacity_threshold") is not None


def test_discharge_respects_power_limit_with_efficiency() -> None:
    """Battery discharge respects power limit even with efficiency in segment chain.

    With 5kW discharge limit and 90% efficiency configured:
    - Battery discharge must never exceed 5kW
    - Efficiency reduces power delivered to grid

    Verifies power_limit and efficiency segments interact correctly - power limit
    is enforced regardless of efficiency losses in the chain.
    """
    from custom_components.haeo.model import Network
    from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_NODE
    from custom_components.haeo.model.elements.battery import BATTERY_POWER_DISCHARGE

    max_discharge_kw = 5.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of capacity to discharge at max for one period
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 15.0,  # Plenty to discharge at 5kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Connection with power limit, efficiency, and pricing
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([max_discharge_kw]),
                    "max_power_target_source": np.array([5.0]),
                },
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": np.array([efficiency]),
                    "efficiency_target_source": np.array([efficiency]),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([-0.50]),  # Discharge pays
                    "price_target_source": np.array([0.10]),
                },
            },
        }
    )

    network.optimize()

    # Verify battery discharge respects power limit
    battery_discharge = network.elements["battery"].outputs()[BATTERY_POWER_DISCHARGE].values[0]
    assert battery_discharge <= max_discharge_kw + 0.001, f"Battery discharge {battery_discharge:.3f}kW exceeds {max_discharge_kw}kW limit"
    # Should discharge at max since it's profitable
    assert battery_discharge >= max_discharge_kw - 0.001, f"Expected max discharge {max_discharge_kw}kW, got {battery_discharge:.3f}kW"


def test_charge_respects_power_limit_with_efficiency() -> None:
    """Battery charge respects power limit even with efficiency in segment chain.

    With 3kW charge limit and 90% efficiency configured:
    - Battery charge must never exceed 3kW
    - Efficiency means grid provides more power than battery stores

    Verifies power_limit and efficiency segments interact correctly.
    """
    from custom_components.haeo.model import Network
    from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_NODE
    from custom_components.haeo.model.elements.battery import BATTERY_POWER_CHARGE

    max_charge_kw = 3.0
    efficiency = 0.9

    network = Network(name="test", periods=np.array([1.0]))

    # Battery with plenty of headroom to charge at max
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": np.array([20.0, 20.0]),
            "initial_charge": 2.0,  # Low charge, plenty of room to accept 3kW for 1 hour
        }
    )

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})

    # Connection with power limit, efficiency, and pricing
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "battery_grid",
            "source": "battery",
            "target": "grid",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([5.0]),
                    "max_power_target_source": np.array([max_charge_kw]),
                },
                "efficiency": {
                    "segment_type": "efficiency",
                    "efficiency_source_target": np.array([efficiency]),
                    "efficiency_target_source": np.array([efficiency]),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.50]),  # Discharge costs
                    "price_target_source": np.array([-0.10]),  # Charging pays
                },
            },
        }
    )

    network.optimize()

    # Verify battery charge respects power limit
    battery_charge = network.elements["battery"].outputs()[BATTERY_POWER_CHARGE].values[0]
    assert battery_charge <= max_charge_kw + 0.001, f"Battery charge {battery_charge:.3f}kW exceeds {max_charge_kw}kW limit"
    # Should charge since it's profitable (exact amount depends on efficiency interaction)
    assert battery_charge > 0, "Expected battery to charge since it's profitable"
