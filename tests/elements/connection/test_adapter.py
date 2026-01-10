"""Tests for connection adapter inputs() and available() functions."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import connection


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_with_no_optional_fields(hass: HomeAssistant) -> None:
    """Connection available() should return True with only required fields."""
    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "name": "c1",
        "source": "node_a",
        "target": "node_b",
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
        "name": "c1",
        "source": "node_a",
        "target": "node_b",
        "max_power_source_target": ["sensor.max_power_st"],
        "max_power_target_source": ["sensor.max_power_ts"],
        "efficiency_source_target": ["sensor.eff_st"],
        "efficiency_target_source": ["sensor.eff_ts"],
        "price_source_target": ["sensor.price_st"],
        "price_target_source": ["sensor.price_ts"],
    }

    result = connection.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_optional_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when a configured optional sensor is missing."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    # max_power_ts sensor is missing

    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "name": "c1",
        "source": "node_a",
        "target": "node_b",
        "max_power_source_target": ["sensor.max_power_st"],
        "max_power_target_source": ["sensor.missing"],
    }

    result = connection.adapter.available(config, hass=hass)
    assert result is False


def test_inputs_returns_input_field_info() -> None:
    """Connection inputs() should return InputFieldInfo tuples for all configurable fields."""
    config: connection.ConnectionConfigSchema = {
        "element_type": "connection",
        "name": "c1",
        "source": "node_a",
        "target": "node_b",
    }

    result = connection.adapter.inputs(config)

    # Should return 6 input fields
    assert len(result) == 6

    # Verify field names
    field_names = [info.field_name for info in result]
    assert "max_power_source_target" in field_names
    assert "max_power_target_source" in field_names
    assert "efficiency_source_target" in field_names
    assert "efficiency_target_source" in field_names
    assert "price_source_target" in field_names
    assert "price_target_source" in field_names
