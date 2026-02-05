"""Tests for grid adapter availability checks."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import grid
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Grid available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {
            "name": "test_grid",
            "connection": as_connection_target("main_bus"),
        },
        grid.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.import_price"]),
            "price_target_source": as_entity_value(["sensor.export_price"]),
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
        grid.SECTION_COMMON: {
            "name": "test_grid",
            "connection": as_connection_target("main_bus"),
        },
        grid.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.missing"]),
            "price_target_source": as_entity_value(["sensor.export_price"]),
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
        grid.SECTION_COMMON: {
            "name": "test_grid",
            "connection": as_connection_target("main_bus"),
        },
        grid.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.import_price"]),
            "price_target_source": as_entity_value(["sensor.missing"]),
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is False


async def test_available_with_constant_prices(hass: HomeAssistant) -> None:
    """Grid available() returns True when prices are constants (no sensors needed)."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {
            "name": "test_grid",
            "connection": as_connection_target("main_bus"),
        },
        grid.SECTION_PRICING: {
            "price_source_target": as_constant_value(0.30),
            "price_target_source": as_constant_value(0.05),
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_available_with_entity_schema_value(hass: HomeAssistant) -> None:
    """Grid available() returns True when price uses entity schema value."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        grid.SECTION_COMMON: {
            "name": "test_grid",
            "connection": as_connection_target("main_bus"),
        },
        grid.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.import_price"]),
            "price_target_source": as_constant_value(0.05),
        },
        grid.SECTION_POWER_LIMITS: {},
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True
