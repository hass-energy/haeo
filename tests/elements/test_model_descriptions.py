"""Test model description functions in elements module."""

from typing import cast

import pytest

from custom_components.haeo.elements import (
    ElementConfigData,
    battery,
    connection,
    constant_load,
    forecast_load,
    get_model_description,
    grid,
    node,
    photovoltaics,
)


def test_battery_get_model_description() -> None:
    """Test battery model description generation."""
    config: battery.BatteryConfigData = {
        "element_type": battery.ELEMENT_TYPE,
        "name": "Test Battery",
        "capacity": 10.0,
        "initial_charge_percentage": 50.0,
        "max_charge_power": 5.0,
        "max_discharge_power": 5.0,
    }

    description = get_model_description(config)

    assert description.startswith("Battery 10.0kWh")
    assert "5.0kW charge" in description


def test_grid_get_model_description() -> None:
    """Test grid model description generation."""
    config: grid.GridConfigData = {
        "element_type": grid.ELEMENT_TYPE,
        "name": "Test Grid",
        "import_price": [0.30, 0.35],
        "export_price": [0.10, 0.12],
        "import_limit": 7.0,
        "export_limit": 3.5,
    }

    description = get_model_description(config)

    assert description == "Grid Import 7.0kW, Export 3.5kW"


def test_connection_get_model_description() -> None:
    """Test connection model description generation."""
    config: connection.ConnectionConfigData = {
        "element_type": connection.ELEMENT_TYPE,
        "name": "Test Connection",
        "source": "source",
        "target": "target",
        "min_power": 2.0,
        "max_power": 4.0,
    }

    description = get_model_description(config)

    assert description == "Connection 2.0kW to 4.0kW"


def test_photovoltaics_get_model_description() -> None:
    """Test photovoltaics model description generation."""
    config: photovoltaics.PhotovoltaicsConfigData = {
        "element_type": photovoltaics.ELEMENT_TYPE,
        "name": "Test PV",
        "forecast": [3.2, 1.5, 0.0],
        "price_production": 0.12,
    }

    description = get_model_description(config)

    assert description == "Solar"


def test_constant_load_get_model_description() -> None:
    """Test constant load model description generation."""
    config: constant_load.ConstantLoadConfigData = {
        "element_type": constant_load.ELEMENT_TYPE,
        "name": "Test Load",
        "power": 2.5,
    }

    description = get_model_description(config)

    assert description == "Constant Load 2.5kW"


def test_forecast_load_get_model_description() -> None:
    """Test forecast load model description generation."""
    config: forecast_load.ForecastLoadConfigData = {
        "element_type": forecast_load.ELEMENT_TYPE,
        "name": "Test Forecast Load",
        "forecast": [1.0, 2.0, 3.0],
    }

    description = get_model_description(config)

    assert description == "Forecast Load"


def test_node_get_model_description() -> None:
    """Test node model description generation."""
    config: node.NodeConfigData = {
        "element_type": node.ELEMENT_TYPE,
        "name": "Test Node",
    }

    description = get_model_description(config)

    assert description == "Node"


def test_unknown_element_type_raises_error() -> None:
    """Test that unknown element type raises ValueError."""
    config = {
        "element_type": "unknown_type",
        "name": "Test",
    }

    with pytest.raises(ValueError, match="Unknown element type"):
        get_model_description(cast("ElementConfigData", config))
