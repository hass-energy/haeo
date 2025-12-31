"""Tests for grid adapter load() and available() functions."""

from collections.abc import Sequence

from homeassistant.core import HomeAssistant

from custom_components.haeo.elements import grid
from custom_components.haeo.elements.grid.schema import (
    DEFAULT_EXPORT_PRICE,
    DEFAULT_IMPORT_PRICE,
)


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


FORECAST_TIMES: Sequence[float] = [0.0, 1800.0]


async def test_available_returns_true_when_sensors_exist(hass: HomeAssistant) -> None:
    """Grid available() should return True when required sensors exist."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.export_price"],
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_available_returns_false_when_import_price_missing(hass: HomeAssistant) -> None:
    """Grid available() should return False when import_price sensor is missing."""
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.missing"],
        "export_price": ["sensor.export_price"],
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is False


async def test_available_returns_false_when_export_price_missing(hass: HomeAssistant) -> None:
    """Grid available() should return False when export_price sensor is missing."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.missing"],
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is False


async def test_load_returns_config_data(hass: HomeAssistant) -> None:
    """Grid load() should return ConfigData with loaded values."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.export_price"],
    }

    result = await grid.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["element_type"] == "grid"
    assert result["name"] == "test_grid"
    assert len(result["import_price"]) == 1
    assert result["import_price"][0] == 0.30


async def test_load_with_optional_limits(hass: HomeAssistant) -> None:
    """Grid load() should include optional constant limit fields."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.export_price"],
        "import_limit": 10.0,
        "export_limit": 5.0,
    }

    result = await grid.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result.get("import_limit") == 10.0
    assert result.get("export_limit") == 5.0


async def test_available_returns_true_for_empty_price_lists(hass: HomeAssistant) -> None:
    """Grid available() should return True when price lists are empty (defaults to constant values)."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": [],
        "export_price": [],
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_load_with_empty_import_price_uses_default(hass: HomeAssistant) -> None:
    """Grid load() should use default import price when import_price list is empty."""
    _set_sensor(hass, "sensor.export_price", "0.05", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": [],
        "export_price": ["sensor.export_price"],
    }

    result = await grid.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["import_price"] == [DEFAULT_IMPORT_PRICE, DEFAULT_IMPORT_PRICE]
    assert result["export_price"][0] == 0.05


async def test_load_with_empty_export_price_uses_default(hass: HomeAssistant) -> None:
    """Grid load() should use default export price when export_price list is empty."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": [],
    }

    result = await grid.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["import_price"][0] == 0.30
    assert result["export_price"] == [DEFAULT_EXPORT_PRICE, DEFAULT_EXPORT_PRICE]


async def test_load_with_both_empty_price_lists_uses_defaults(hass: HomeAssistant) -> None:
    """Grid load() should use default prices when both lists are empty."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": [],
        "export_price": [],
    }

    result = await grid.adapter.load(config, hass=hass, forecast_times=FORECAST_TIMES)

    assert result["import_price"] == [DEFAULT_IMPORT_PRICE, DEFAULT_IMPORT_PRICE]
    assert result["export_price"] == [DEFAULT_EXPORT_PRICE, DEFAULT_EXPORT_PRICE]
