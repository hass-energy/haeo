"""Tests for inverter adapter load() and available() functions."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import inverter


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Inverter available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_first_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_dc_to_ac sensor is missing."""
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")
    # max_power_dc_to_ac is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.missing",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_second_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_ac_to_dc sensor is missing."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    # max_power_ac_to_dc sensor is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.missing",
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Inverter load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
    }

    result = await inverter.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "inverter"
    assert result["name"] == "test_inverter"
    assert len(result["max_power_dc_to_ac"]) == 1
    assert result["max_power_dc_to_ac"][0] == 5.0


async def test_load_with_optional_efficiency(hass: HomeAssistant) -> None:
    """Inverter load() should include optional constant efficiency fields."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": "sensor.max_dc_to_ac",
        "max_power_ac_to_dc": "sensor.max_ac_to_dc",
        "efficiency_dc_to_ac": 97.0,
        "efficiency_ac_to_dc": 95.0,
    }

    result = await inverter.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result.get("efficiency_dc_to_ac") == 97.0
    assert result.get("efficiency_ac_to_dc") == 95.0
