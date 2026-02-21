"""Tests for solar adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import solar
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value

from ..conftest import set_forecast_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Solar available() should return True when forecast sensor exists."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        solar.SECTION_COMMON: {
            "name": "test_solar",
            "connection": as_connection_target("dc_bus"),
        },
        solar.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.forecast"])},
        solar.SECTION_PRICING: {"price_source_target": as_constant_value(0.0)},
        solar.SECTION_CURTAILMENT: {"curtailment": as_constant_value(value=True)},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Solar available() should return False when forecast sensor is missing."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        solar.SECTION_COMMON: {
            "name": "test_solar",
            "connection": as_connection_target("dc_bus"),
        },
        solar.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.missing"])},
        solar.SECTION_PRICING: {"price_source_target": as_constant_value(0.0)},
        solar.SECTION_CURTAILMENT: {"curtailment": as_constant_value(value=True)},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False
