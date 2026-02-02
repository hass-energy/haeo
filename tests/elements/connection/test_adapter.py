"""Tests for connection adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import connection


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_with_no_optional_fields(hass: HomeAssistant) -> None:
    """Connection available() should return True with only required fields."""
    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "common": {"name": "c1"},
        "endpoints": {"source": "node_a", "target": "node_b"},
        "power_limits": {},
        "pricing": {},
        "advanced": {},
    }

    result = connection.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_true_when_optional_sensors_exist(hass: HomeAssistant) -> None:
    """Connection available() should return True when all configured sensors exist."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    _set_sensor(hass, "sensor.max_power_ts", "3.0", "kW")
    _set_sensor(hass, "sensor.eff_st", "95.0", "%")
    _set_sensor(hass, "sensor.eff_ts", "90.0", "%")
    _set_sensor(hass, "sensor.price_st", "0.10", "$/kWh")
    _set_sensor(hass, "sensor.price_ts", "0.05", "$/kWh")

    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "common": {"name": "c1"},
        "endpoints": {"source": "node_a", "target": "node_b"},
        "power_limits": {
            "max_power_source_target": "sensor.max_power_st",
            "max_power_target_source": "sensor.max_power_ts",
        },
        "pricing": {
            "price_source_target": "sensor.price_st",
            "price_target_source": "sensor.price_ts",
        },
        "advanced": {
            "efficiency_source_target": "sensor.eff_st",
            "efficiency_target_source": "sensor.eff_ts",
        },
    }

    result = connection.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_optional_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when a configured optional sensor is missing."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    # max_power_ts sensor is missing

    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "common": {"name": "c1"},
        "endpoints": {"source": "node_a", "target": "node_b"},
        "power_limits": {
            "max_power_source_target": "sensor.max_power_st",
            "max_power_target_source": "sensor.missing",
        },
        "pricing": {},
        "advanced": {},
    }

    result = connection.adapter.available(config, hass=hass)
    assert result is False
