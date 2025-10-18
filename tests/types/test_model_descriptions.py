"""Test model description functions in types module."""

import pytest

from custom_components.haeo.types import get_model_description


def test_battery_get_model_description() -> None:
    """Test battery model description generation."""
    config = {
        "element_type": "battery",
        "name": "Test Battery",
        "capacity": 10000.0,
        "max_charge_power": 5000.0,
        "max_discharge_power": 5000.0,
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0
    assert "Battery" in description or "battery" in description


def test_grid_get_model_description() -> None:
    """Test grid model description generation."""
    config = {
        "element_type": "grid",
        "name_value": "Test Grid",
        "import_limit_value": 10000.0,
        "export_limit_value": 5000.0,
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_connection_get_model_description() -> None:
    """Test connection model description generation."""
    config = {
        "element_type": "connection",
        "name_value": "Test Connection",
        "source_value": "source",
        "target_value": "target",
        "capacity_value": 1000.0,
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_photovoltaics_get_model_description() -> None:
    """Test photovoltaics model description generation."""
    config = {
        "element_type": "photovoltaics",
        "name_value": "Test PV",
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_constant_load_get_model_description() -> None:
    """Test constant load model description generation."""
    config = {
        "element_type": "constant_load",
        "name": "Test Load",
        "power": 2000.0,
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_forecast_load_get_model_description() -> None:
    """Test forecast load model description generation."""
    config = {
        "element_type": "forecast_load",
        "name_value": "Test Forecast Load",
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_node_get_model_description() -> None:
    """Test node model description generation."""
    config = {
        "element_type": "node",
        "name_value": "Test Node",
    }

    description = get_model_description(config)

    assert isinstance(description, str)
    assert len(description) > 0


def test_unknown_element_type_raises_error() -> None:
    """Test that unknown element type raises ValueError."""
    config = {
        "element_type": "unknown_type",
        "name_value": "Test",
    }

    with pytest.raises(ValueError, match="Unknown element type"):
        get_model_description(config)
