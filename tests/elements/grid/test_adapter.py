"""Tests for grid adapter build_config_data() and available() functions."""

from homeassistant.core import HomeAssistant
import numpy as np

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


def test_build_config_data_returns_config_data() -> None:
    """build_config_data() should return ConfigData with loaded values."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.export_price"],
    }
    loaded_values = {
        "import_price": np.array([0.30, 0.30]),
        "export_price": np.array([0.05, 0.05]),
    }

    result = grid.adapter.build_config_data(loaded_values, config)

    assert result["element_type"] == "grid"
    assert result["name"] == "test_grid"
    np.testing.assert_array_equal(result["import_price"], [0.30, 0.30])
    np.testing.assert_array_equal(result["export_price"], [0.05, 0.05])


def test_build_config_data_includes_optional_limits() -> None:
    """build_config_data() should include optional limit fields when provided."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import_price"],
        "export_price": ["sensor.export_price"],
    }
    loaded_values = {
        "import_price": np.array([0.30, 0.30]),
        "export_price": np.array([0.05, 0.05]),
        "import_limit": np.array([10.0, 10.0]),
        "export_limit": np.array([5.0, 5.0]),
    }

    result = grid.adapter.build_config_data(loaded_values, config)

    assert result.get("import_limit") is not None
    np.testing.assert_array_equal(result["import_limit"], [10.0, 10.0])
    assert result.get("export_limit") is not None
    np.testing.assert_array_equal(result["export_limit"], [5.0, 5.0])


async def test_available_with_constant_prices(hass: HomeAssistant) -> None:
    """Grid available() returns True when prices are constants (no sensors needed)."""
    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": 0.30,  # Constant
        "export_price": 0.05,  # Constant
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True


async def test_available_with_single_entity_string(hass: HomeAssistant) -> None:
    """Grid available() returns True when price is a single entity string."""
    _set_sensor(hass, "sensor.import_price", "0.30", "$/kWh")

    config: grid.GridConfigSchema = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": "sensor.import_price",  # Single string, not list
        "export_price": 0.05,  # Constant
    }

    result = grid.adapter.available(config, hass=hass)
    assert result is True
