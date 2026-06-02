"""Tests for connection adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType, connection
from custom_components.haeo.elements.availability import schema_config_available


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_with_no_optional_fields(hass: HomeAssistant) -> None:
    """Connection available() should return True with only required fields."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {},
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_true_when_optional_sensors_exist(hass: HomeAssistant) -> None:
    """Connection available() should return True when all configured sensors exist."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    _set_sensor(hass, "sensor.eff_st", "95.0", "%")
    _set_sensor(hass, "sensor.price_st", "0.10", "$/kWh")

    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_power_st"]),
        },
        connection.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.price_st"]),
        },
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_entity_value(["sensor.eff_st"]),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_optional_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when a configured optional sensor is missing."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.missing"]),
        },
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_false_when_efficiency_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when efficiency sensor is missing."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {},
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_entity_value(["sensor.missing"]),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_true_with_constant_values(hass: HomeAssistant) -> None:
    """Connection available() should return True when values are constants."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_constant_value(5.0),
        },
        connection.SECTION_PRICING: {
            "price_source_target": as_constant_value(0.1),
        },
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_constant_value(0.9),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True
