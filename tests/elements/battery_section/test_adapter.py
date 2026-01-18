"""Tests for battery_section adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import battery_section


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Battery section available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    _set_sensor(hass, "sensor.initial", "50.0", "%")

    config: battery_section.BatterySectionConfigSchema = {
        "element_type": "battery_section",
        "name": "test_section",
        "capacity": "sensor.capacity",
        "initial_charge": "sensor.initial",
    }

    result = battery_section.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_sensor_missing(hass: HomeAssistant) -> None:
    """Battery section available() should return False when a required sensor is missing."""
    _set_sensor(hass, "sensor.capacity", "10.0", "kWh")
    # Not setting initial_charge sensor

    config: battery_section.BatterySectionConfigSchema = {
        "element_type": "battery_section",
        "name": "test_section",
        "capacity": "sensor.capacity",
        "initial_charge": "sensor.missing",
    }

    result = battery_section.adapter.available(config, hass=hass)
    assert result is False
