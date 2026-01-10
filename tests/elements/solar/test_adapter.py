"""Tests for solar adapter inputs() and available() functions."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import solar

from ..conftest import set_forecast_sensor


async def test_available_returns_true_when_forecast_sensor_exists(hass: HomeAssistant) -> None:
    """Solar available() should return True when forecast sensor exists."""
    set_forecast_sensor(hass, "sensor.forecast", "5.0", [{"datetime": "2024-01-01T00:00:00Z", "value": 5.0}], "kW")

    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_forecast_sensor_missing(hass: HomeAssistant) -> None:
    """Solar available() should return False when forecast sensor is missing."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.missing"],
    }

    result = solar.adapter.available(config, hass=hass)
    assert result is False


def test_inputs_returns_field_definitions() -> None:
    """Solar inputs() should return input field definitions."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
    }

    result = solar.adapter.inputs(config)

    # Should return tuple with 3 fields
    assert len(result) == 3

    # Check field names
    field_names = [field.field_name for field in result]
    assert "forecast" in field_names
    assert "price_production" in field_names
    assert "curtailment" in field_names


def test_inputs_has_correct_entity_descriptions() -> None:
    """Solar inputs() should have correct entity description types."""
    config: solar.SolarConfigSchema = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "dc_bus",
        "forecast": ["sensor.forecast"],
    }

    result = solar.adapter.inputs(config)

    # Find each field
    fields_by_name = {field.field_name: field for field in result}

    # Forecast and price_production should be NumberEntityDescription
    assert type(fields_by_name["forecast"].entity_description).__name__ == "NumberEntityDescription"
    assert type(fields_by_name["price_production"].entity_description).__name__ == "NumberEntityDescription"

    # Curtailment should be SwitchEntityDescription
    assert type(fields_by_name["curtailment"].entity_description).__name__ == "SwitchEntityDescription"
