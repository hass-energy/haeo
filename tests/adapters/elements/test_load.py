"""Tests for load element adapter availability and inputs."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.adapters.elements.load import adapter as load_adapter
from custom_components.haeo.elements.availability import schema_config_available
from custom_components.haeo.schema import as_connection_target, as_entity_value
from custom_components.haeo.schema.elements import load as load_element

from .conftest import set_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Load available() should return True when forecast sensor exists."""
    set_sensor(hass, "sensor.power", "2.5", "kW")

    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        load_element.SECTION_COMMON: {
            "name": "test_load",
            "connection": as_connection_target("main_bus"),
        },
        load_element.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.power"])},
        load_element.SECTION_PRICING: {},
        load_element.SECTION_CURTAILMENT: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Load available() should return False when forecast sensor is missing."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        load_element.SECTION_COMMON: {
            "name": "test_load",
            "connection": as_connection_target("main_bus"),
        },
        load_element.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.missing"])},
        load_element.SECTION_PRICING: {},
        load_element.SECTION_CURTAILMENT: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


def test_inputs_returns_input_fields() -> None:
    """inputs() should return input field definitions for load."""
    config: load_element.LoadConfigSchema = {
        "element_type": "load",
        load_element.SECTION_COMMON: {
            "name": "test_load",
            "connection": as_connection_target("main_bus"),
        },
        load_element.SECTION_FORECAST: {"forecast": as_entity_value(["sensor.power"])},
        load_element.SECTION_PRICING: {},
        load_element.SECTION_CURTAILMENT: {},
    }

    input_fields = load_adapter.inputs(config)

    assert load_element.SECTION_FORECAST in input_fields
    assert "forecast" in input_fields[load_element.SECTION_FORECAST]

    assert load_element.SECTION_PRICING in input_fields
    assert "price_target_source" in input_fields[load_element.SECTION_PRICING]

    assert load_element.SECTION_CURTAILMENT in input_fields
    assert "curtailment" in input_fields[load_element.SECTION_CURTAILMENT]
