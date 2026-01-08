"""Tests for battery adapter load() and available() functions."""

from collections.abc import Sequence

import pytest
from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import battery
from custom_components.haeo.elements.battery import sum_output_data
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.output_data import OutputData


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0, 3600.0]  # 3 fence posts = 2 periods


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
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": ["sensor.max_charge"],
        "max_discharge_power": ["sensor.max_discharge"],
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
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": ["sensor.max_charge"],
        "max_discharge_power": ["sensor.missing"],
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
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.missing"],
        "max_charge_power": ["sensor.max_charge"],
        "max_discharge_power": ["sensor.max_discharge"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Battery load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "5.0", "kW")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": ["sensor.max_charge"],
        "max_discharge_power": ["sensor.max_discharge"],
    }

    result = await battery.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "battery"
    assert result["name"] == "test_battery"
    assert len(result["capacity"]) == 2  # 3 fence posts = 2 periods
    assert result["capacity"][0] == 10.0
    assert result["max_charge_power"][0] == 5.0
    assert result["max_discharge_power"][0] == 5.0


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


async def test_load_with_optional_time_series_fields(hass: HomeAssistant) -> None:
    """Battery load() should load optional time series fields when configured."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    _set_sensor(hass, "sensor.max_charge", "5.0", "kW")
    _set_sensor(hass, "sensor.max_discharge", "6.0", "kW")
    _set_sensor(hass, "sensor.discharge_cost", "0.05", "$/kWh")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": ["sensor.max_charge"],
        "max_discharge_power": ["sensor.max_discharge"],
        "discharge_cost": ["sensor.discharge_cost"],
    }

    result = await battery.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "battery"
    assert "max_charge_power" in result
    assert result["max_charge_power"][0] == 5.0
    assert "max_discharge_power" in result
    assert result["max_discharge_power"][0] == 6.0
    assert "discharge_cost" in result
    assert result["discharge_cost"][0] == 0.05


async def test_load_with_optional_scalar_fields(hass: HomeAssistant) -> None:
    """Battery load() should load optional scalar fields when configured.

    Scalar values are broadcast to time series when loaded.
    """
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": 5.0,
        "max_discharge_power": 5.0,
        "early_charge_incentive": 0.005,
        "undercharge_percentage": 10.0,
        "overcharge_percentage": 90.0,
    }

    result = await battery.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "battery"
    # Scalar values are broadcast to time series
    assert result.get("early_charge_incentive") == [0.005, 0.005]
    assert result.get("undercharge_percentage") == [10.0, 10.0]
    assert result.get("overcharge_percentage") == [90.0, 90.0]
