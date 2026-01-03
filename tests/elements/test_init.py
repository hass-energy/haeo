"""Tests for elements module __init__.py functions."""

from typing import Any

import pytest

from custom_components.haeo.elements import ELEMENT_CONFIG_SCHEMAS, is_element_config_schema


@pytest.mark.parametrize(
    "input_data",
    [
        [1, 2, 3],
        "not a config",
        None,
    ],
)
def test_is_not_element_config_schema(input_data: Any) -> None:
    """Test is_element_config_schema with non-Mapping input."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        {"element_type": "unknown_type", "name": "test"},  # Unknown element type
        {"name": "test"},  # Missing element_type
        {"element_type": "battery"},  # Missing all required fields
        {"element_type": "battery", "name": "test"},  # Missing required battery fields
        {"element_type": "connection", "name": "test", "source": "a"},  # Missing target
    ],
)
def test_is_element_config_schema_invalid_structure(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema with invalid element structure."""
    assert is_element_config_schema(input_data) is False


@pytest.mark.parametrize(
    "input_data",
    [
        # Wrong type for name (should be str)
        {
            "element_type": "node",
            "name": 123,
            "is_source": False,
            "is_sink": False,
        },
        # Wrong type for connection (should be str)
        {
            "element_type": "grid",
            "name": "test",
            "connection": ["list_not_str"],
            "import_price": ["sensor.import"],
            "export_price": ["sensor.export"],
        },
        # Wrong type for forecast (should be list or float, not plain str)
        {
            "element_type": "solar",
            "name": "test",
            "connection": "bus",
            "forecast": "not_a_list",
        },
        # Wrong type for capacity (bool is rejected - bools are explicitly excluded from
        # constant value handling even though bool is a subclass of int in Python)
        {
            "element_type": "battery",
            "name": "test",
            "connection": "bus",
            "capacity": True,
            "initial_charge_percentage": ["sensor.soc"],
        },
    ],
)
def test_is_element_config_schema_wrong_field_types(input_data: dict[str, Any]) -> None:
    """Test is_element_config_schema rejects fields with wrong types for required fields."""
    assert is_element_config_schema(input_data) is False


def test_is_element_config_schema_valid_node() -> None:
    """Test is_element_config_schema with valid node config."""
    valid_config = {
        "element_type": "node",
        "name": "test_node",
        "is_source": False,
        "is_sink": False,
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_node_minimal() -> None:
    """Test is_element_config_schema with minimal node config (optional fields omitted)."""
    valid_config = {
        "element_type": "node",
        "name": "test_node",
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery() -> None:
    """Test is_element_config_schema with valid battery config."""
    valid_config = {
        "element_type": "battery",
        "name": "test_battery",
        "connection": "main_bus",
        "capacity": ["sensor.capacity"],
        "initial_charge_percentage": ["sensor.soc"],
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid() -> None:
    """Test is_element_config_schema with valid grid config."""
    valid_config = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": ["sensor.import"],
        "export_price": ["sensor.export"],
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_grid_minimal() -> None:
    """Test is_element_config_schema with minimal valid grid config (prices required)."""
    valid_config = {
        "element_type": "grid",
        "name": "test_grid",
        "connection": "main_bus",
        "import_price": 0.10,
        "export_price": 0.05,
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_connection() -> None:
    """Test is_element_config_schema with valid connection config."""
    valid_config = {
        "element_type": "connection",
        "name": "test_connection",
        "source": "battery",
        "target": "grid",
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_load() -> None:
    """Test is_element_config_schema with valid load config."""
    valid_config = {
        "element_type": "load",
        "name": "test_load",
        "connection": "main_bus",
        "forecast": ["sensor.load_forecast"],
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_solar() -> None:
    """Test is_element_config_schema with valid solar config."""
    valid_config = {
        "element_type": "solar",
        "name": "test_solar",
        "connection": "main_bus",
        "forecast": ["sensor.solar_forecast"],
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_inverter() -> None:
    """Test is_element_config_schema with valid inverter config."""
    valid_config = {
        "element_type": "inverter",
        "name": "test_inverter",
        "connection": "ac_bus",
        "max_power_dc_to_ac": ["sensor.dc_to_ac"],
        "max_power_ac_to_dc": ["sensor.ac_to_dc"],
    }
    assert is_element_config_schema(valid_config) is True


def test_is_element_config_schema_valid_battery_section() -> None:
    """Test is_element_config_schema with valid battery_section config."""
    valid_config = {
        "element_type": "battery_section",
        "name": "test_section",
        "capacity": ["sensor.capacity"],
        "initial_charge": ["sensor.charge"],
    }
    assert is_element_config_schema(valid_config) is True


def test_config_schemas_match_element_types() -> None:
    """Ensure ELEMENT_CONFIG_SCHEMAS has an entry for every registered element type."""
    from custom_components.haeo.elements import ELEMENT_TYPES

    for element_type in ELEMENT_TYPES:
        assert element_type in ELEMENT_CONFIG_SCHEMAS, f"Missing config schema for {element_type}"
