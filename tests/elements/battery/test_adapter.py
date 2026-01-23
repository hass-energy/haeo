"""Tests for battery adapter config handling and model elements."""

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.elements import battery
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_BATTERY, MODEL_ELEMENT_TYPE_CONNECTION
from custom_components.haeo.model.elements.segments import is_efficiency_spec


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.max_discharge",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_required_power_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required power sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    # max_discharge_power sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.missing",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_capacity_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when capacity sensor is missing."""
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    # capacity sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.missing_capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_required_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")
    # initial_charge_percentage sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.missing",
        "max_charge_power": "sensor.max_charge",
        "max_discharge_power": "sensor.max_discharge",
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_list_entity_ids_all_exist(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] entity IDs all exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.discharge_cost_1", "0.05", "$/kWh")
    _set_sensor(hass, "sensor.discharge_cost_2", "0.06", "$/kWh")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        # List of entity IDs for chained forecasts
        "discharge_cost": ["sensor.discharge_cost_1", "sensor.discharge_cost_2"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


async def test_available_with_list_entity_ids_one_missing(hass: HomeAssistant) -> None:
    """Battery available() returns False when list[str] entity ID has one missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.discharge_cost_1", "0.05", "$/kWh")
    # sensor.discharge_cost_2 is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        # List of entity IDs where one is missing
        "discharge_cost": ["sensor.discharge_cost_1", "sensor.missing"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_empty_list_returns_true(hass: HomeAssistant) -> None:
    """Battery available() returns True when list[str] is empty."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    # This tests the `if value else True` branch for empty lists
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
        "discharge_cost": [],  # Empty list
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


def test_model_elements_omits_efficiency_when_missing() -> None:
    """model_elements() should leave efficiency to model defaults when missing."""
    config_data: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([0.5, 0.5]),
    }

    elements = battery.adapter.model_elements(config_data)

    battery_element = next(element for element in elements if element["element_type"] == MODEL_ELEMENT_TYPE_BATTERY and element["name"] == "test_battery")
    np.testing.assert_array_equal(battery_element["capacity"], [10.0, 10.0, 10.0])

    connection = next(element for element in elements if element["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION and element["name"] == "test_battery:connection")
    segments = connection.get("segments")
    assert segments is not None
    efficiency_segment = segments.get("efficiency")
    assert efficiency_segment is not None
    assert is_efficiency_spec(efficiency_segment)
    assert efficiency_segment.get("efficiency_source_target") is None
    assert efficiency_segment.get("efficiency_target_source") is None


def test_model_elements_passes_efficiency_when_present() -> None:
    """model_elements() should pass through provided efficiency values."""
    config_data: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([0.5, 0.5]),
        "efficiency": np.array([0.95, 0.95]),
    }

    elements = battery.adapter.model_elements(config_data)

    connection = next(element for element in elements if element["element_type"] == MODEL_ELEMENT_TYPE_CONNECTION and element["name"] == "test_battery:connection")
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
