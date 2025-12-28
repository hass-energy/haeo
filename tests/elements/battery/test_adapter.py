"""Tests for battery adapter load() and available() functions."""

from collections.abc import Sequence

import pytest
from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import battery
from custom_components.haeo.elements.battery import sum_output_data
from custom_components.haeo.model.output_data import OutputData


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_optional_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a configured optional sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")
    # max_charge_power sensor configured but missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
        "max_charge_power": ["sensor.missing"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_required_sensor_missing(hass: HomeAssistant) -> None:
    """Battery available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    # initial_charge_percentage sensor is missing

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.missing"],
    }

    result = battery.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Battery load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: battery.BatteryConfigSchema = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.initial"],
    }

    result = await battery.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "battery"
    assert result["name"] == "test_battery"
    assert len(result["capacity"]) == 1
    assert result["capacity"][0] == 10.0


def test_sum_output_data_raises_on_empty_list() -> None:
    """sum_output_data raises ValueError when given an empty list."""
    with pytest.raises(ValueError, match="Cannot sum empty list of outputs"):
        sum_output_data([])


def test_sum_output_data_sums_multiple_outputs() -> None:
    """sum_output_data correctly sums values from multiple OutputData objects."""
    output1 = OutputData(
        type="power",
        unit="kW",
        values=(1.0, 2.0, 3.0),
        direction="+",
        advanced=False,
    )
    output2 = OutputData(
        type="power",
        unit="kW",
        values=(4.0, 5.0, 6.0),
        direction="+",
        advanced=False,
    )

    result = sum_output_data([output1, output2])

    assert result.type == "power"
    assert result.unit == "kW"
    assert result.values == (5.0, 7.0, 9.0)
    assert result.direction == "+"
    assert result.advanced is False
