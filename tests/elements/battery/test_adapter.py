"""Tests for battery adapter build_config_data() and available() functions."""

from homeassistant.core import HomeAssistant
import numpy as np
import pytest

from custom_components.haeo.elements import battery
from custom_components.haeo.elements.battery import sum_output_data
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


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


def test_sum_output_data_raises_on_empty_list() -> None:
    """sum_output_data raises ValueError when given an empty list."""
    with pytest.raises(ValueError, match="Cannot sum empty list of outputs"):
        sum_output_data([])


def test_sum_output_data_sums_multiple_outputs() -> None:
    """sum_output_data correctly sums values from multiple OutputData objects."""
    output1 = OutputData(
        type=OutputType.POWER,
        unit="kW",
        values=(1.0, 2.0, 3.0),
        direction="+",
        advanced=False,
    )
    output2 = OutputData(
        type=OutputType.POWER,
        unit="kW",
        values=(4.0, 5.0, 6.0),
        direction="+",
        advanced=False,
    )

    result = sum_output_data([output1, output2])

    assert result.type == OutputType.POWER
    assert result.unit == "kW"
    assert result.values == (5.0, 7.0, 9.0)
    assert result.direction == "+"
    assert result.advanced is False


# Tests for build_config_data() - single source of truth for ConfigData construction


def test_build_config_data_applies_defaults_for_optional_fields() -> None:
    """build_config_data() should apply defaults for optional fields not in loaded_values."""
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",  # Will be ignored, using loaded_values
        "initial_charge_percentage": "sensor.initial",  # Will be ignored
    }

    # Only provide required fields, no optional fields with defaults
    loaded_values: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),  # 3 boundaries
        "initial_charge_percentage": np.array([50.0, 50.0]),  # 2 intervals
    }

    result = battery.adapter.build_config_data(loaded_values, config)

    # Required fields from loaded_values
    np.testing.assert_array_equal(result["capacity"], [10.0, 10.0, 10.0])
    np.testing.assert_array_equal(result["initial_charge_percentage"], [50.0, 50.0])

    # Defaults applied for optional fields (boundaries: 3 values, intervals: 2 values)
    min_charge_percentage = result.get("min_charge_percentage")
    assert min_charge_percentage is not None
    np.testing.assert_array_equal(min_charge_percentage, [0.0, 0.0, 0.0])  # Default 0.0, boundaries
    max_charge_percentage = result.get("max_charge_percentage")
    assert max_charge_percentage is not None
    np.testing.assert_array_equal(max_charge_percentage, [100.0, 100.0, 100.0])  # Default 100.0, boundaries
    efficiency = result.get("efficiency")
    assert efficiency is not None
    np.testing.assert_array_equal(efficiency, [99.0, 99.0])  # Default 99.0, intervals


def test_build_config_data_uses_provided_values_over_defaults() -> None:
    """build_config_data() should use loaded values instead of defaults when provided."""
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    loaded_values: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([20.0, 20.0, 20.0]),
        "initial_charge_percentage": np.array([75.0, 75.0]),
        # Provide non-default values for optional fields
        "min_charge_percentage": np.array([10.0, 10.0, 10.0]),
        "max_charge_percentage": np.array([90.0, 90.0, 90.0]),
        "efficiency": np.array([95.0, 95.0]),
    }

    result = battery.adapter.build_config_data(loaded_values, config)

    # Should use provided values, not defaults
    min_charge_percentage = result.get("min_charge_percentage")
    assert min_charge_percentage is not None
    np.testing.assert_array_equal(min_charge_percentage, [10.0, 10.0, 10.0])
    max_charge_percentage = result.get("max_charge_percentage")
    assert max_charge_percentage is not None
    np.testing.assert_array_equal(max_charge_percentage, [90.0, 90.0, 90.0])
    efficiency = result.get("efficiency")
    assert efficiency is not None
    np.testing.assert_array_equal(efficiency, [95.0, 95.0])


def test_build_config_data_includes_optional_fields_without_defaults() -> None:
    """build_config_data() should include optional fields without defaults when provided."""
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    loaded_values: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([50.0, 50.0]),
        # Optional fields without defaults
        "max_charge_power": np.array([5.0, 5.0]),
        "max_discharge_power": np.array([6.0, 6.0]),
        "early_charge_incentive": np.array([0.002, 0.002]),
    }

    result = battery.adapter.build_config_data(loaded_values, config)

    max_charge_power = result.get("max_charge_power")
    assert max_charge_power is not None
    np.testing.assert_array_equal(max_charge_power, [5.0, 5.0])
    max_discharge_power = result.get("max_discharge_power")
    assert max_discharge_power is not None
    np.testing.assert_array_equal(max_discharge_power, [6.0, 6.0])
    early_charge_incentive = result.get("early_charge_incentive")
    assert early_charge_incentive is not None
    np.testing.assert_array_equal(early_charge_incentive, [0.002, 0.002])


def test_build_config_data_omits_optional_fields_not_provided() -> None:
    """build_config_data() should omit optional fields without defaults when not in loaded_values."""
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    loaded_values: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([50.0, 50.0]),
        # Not providing max_charge_power, max_discharge_power, etc.
    }

    result = battery.adapter.build_config_data(loaded_values, config)

    # Optional fields without defaults should not be present
    assert "max_charge_power" not in result
    assert "max_discharge_power" not in result
    assert "discharge_cost" not in result
    assert "early_charge_incentive" not in result


def test_build_config_data_preserves_non_input_fields_from_config() -> None:
    """build_config_data() should use non-input fields from config (e.g., connection)."""
    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "my_battery",
        "connection": "dc_bus",
        "capacity": "sensor.capacity",
        "initial_charge_percentage": "sensor.initial",
    }

    loaded_values: battery.BatteryConfigData = {
        "element_type": "battery",
        "name": "my_battery",
        "connection": "dc_bus",
        "capacity": np.array([10.0, 10.0, 10.0]),
        "initial_charge_percentage": np.array([50.0, 50.0]),
    }

    result = battery.adapter.build_config_data(loaded_values, config)

    # Non-input fields come from config
    assert result["element_type"] == "battery"
    assert result["name"] == "my_battery"
    assert result["connection"] == "dc_bus"
