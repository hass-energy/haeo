"""Tests for inverter adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import inverter


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Inverter available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "common": {"name": "test_inverter", "connection": "ac_bus"},
        "power_limits": {
            "max_power_source_target": "sensor.max_dc_to_ac",
            "max_power_target_source": "sensor.max_ac_to_dc",
        },
        "advanced": {},
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_first_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_dc_to_ac sensor is missing."""
    _set_sensor(hass, "sensor.max_ac_to_dc", "5.0", "kW")
    # max_power_dc_to_ac is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "common": {"name": "test_inverter", "connection": "ac_bus"},
        "power_limits": {
            "max_power_source_target": "sensor.missing",
            "max_power_target_source": "sensor.max_ac_to_dc",
        },
        "advanced": {},
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_second_sensor_missing(hass: HomeAssistant) -> None:
    """Inverter available() should return False when max_power_ac_to_dc sensor is missing."""
    _set_sensor(hass, "sensor.max_dc_to_ac", "5.0", "kW")
    # max_power_ac_to_dc sensor is missing

    config: inverter.InverterConfigSchema = {
        "element_type": "inverter",
        "common": {"name": "test_inverter", "connection": "ac_bus"},
        "power_limits": {
            "max_power_source_target": "sensor.max_dc_to_ac",
            "max_power_target_source": "sensor.missing",
        },
        "advanced": {},
    }

    result = inverter.adapter.available(config, hass=hass)
    assert result is False
