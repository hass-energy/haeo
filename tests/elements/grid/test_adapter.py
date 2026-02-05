"""Tests for grid adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import grid


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Grid available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": "main_bus"},
        grid.SECTION_PRICING: {
            "price_source_target": ["sensor.import_price"],
            "price_target_source": ["sensor.export_price"],
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_import_price_missing(hass: HomeAssistant) -> None:
    """Grid available() should return False when import_price sensor is missing."""
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": "main_bus"},
        grid.SECTION_PRICING: {
            "price_source_target": ["sensor.missing"],
            "price_target_source": ["sensor.export_price"],
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_export_price_missing(hass: HomeAssistant) -> None:
    """Grid available() should return False when export_price sensor is missing."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": "main_bus"},
        grid.SECTION_PRICING: {
            "price_source_target": ["sensor.import_price"],
            "price_target_source": ["sensor.missing"],
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_constant_prices(hass: HomeAssistant) -> None:
    """Grid available() returns True when prices are constants (no sensors needed)."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": "main_bus"},
        grid.SECTION_PRICING: {
            "price_source_target": 0.30,  # Constant
            "price_target_source": 0.05,  # Constant
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_available_with_single_entity_string(hass: HomeAssistant) -> None:
    """Grid available() returns True when price is a single entity string."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {"name": "test_grid", "connection": "main_bus"},
        grid.SECTION_PRICING: {
            "price_source_target": "sensor.import_price",  # Single string, not list
            "price_target_source": 0.05,  # Constant
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True
