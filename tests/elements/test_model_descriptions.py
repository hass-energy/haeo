"""Test model description functions in elements module."""

from typing import cast

import pytest

from custom_components.haeo.elements import (
    ElementConfigSchema,
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
    config: battery.BatteryConfigSchema = {
        "element_type": battery.ELEMENT_TYPE,
        "name": "Test Battery",
        "capacity": 10.0,
        "initial_charge_percentage": "sensor.battery_soc",
        "max_charge_power": 5.0,
        "max_discharge_power": 5.0,
    }

    description = get_model_description(config)

    assert description.startswith("Battery 10.0kWh")
    assert "5.0kW charge" in description


def test_grid_get_model_description() -> None:
    """Test grid model description generation."""
    config: grid.GridConfigSchema = {
        "element_type": grid.ELEMENT_TYPE,
        "name": "Test Grid",
        "import_price": {
            "live": ["sensor.import_price"],
            "forecast": [],
        },
        "export_price": {
            "live": ["sensor.export_price"],
            "forecast": [],
        },
        "import_limit": 7.0,
        "export_limit": 3.5,
    }

    description = get_model_description(config)

    assert description == "Grid Import 7.0kW, Export 3.5kW"


def test_grid_get_model_description_import_only() -> None:
    """Test grid model description with only import limit."""
    config: grid.GridConfigSchema = {
        "element_type": grid.ELEMENT_TYPE,
        "name": "Test Grid",
        "import_price": {
            "live": ["sensor.import_price"],
            "forecast": [],
        },
        "export_price": {
            "live": ["sensor.export_price"],
            "forecast": [],
        },
        "import_limit": 7.0,
    }

    description = get_model_description(config)

    assert description == "Grid Import 7.0kW"


def test_grid_get_model_description_export_only() -> None:
    """Test grid model description with only export limit."""
    config: grid.GridConfigSchema = {
        "element_type": grid.ELEMENT_TYPE,
        "name": "Test Grid",
        "import_price": {
            "live": ["sensor.import_price"],
            "forecast": [],
        },
        "export_price": {
            "live": ["sensor.export_price"],
            "forecast": [],
        },
        "export_limit": 3.5,
    }

    description = get_model_description(config)

    assert description == "Grid Export 3.5kW"


def test_grid_get_model_description_no_limits() -> None:
    """Test grid model description with no limits."""
    config: grid.GridConfigSchema = {
        "element_type": grid.ELEMENT_TYPE,
        "name": "Test Grid",
        "import_price": {
            "live": ["sensor.import_price"],
            "forecast": [],
        },
        "export_price": {
            "live": ["sensor.export_price"],
            "forecast": [],
        },
    }

    description = get_model_description(config)

    assert description == "Grid Connection"


def test_connection_get_model_description() -> None:
    """Test connection model description generation."""
    config: connection.ConnectionConfigSchema = {
        "element_type": connection.ELEMENT_TYPE,
        "name": "Test Connection",
        "source": "source",
        "target": "target",
        "min_power": 2.0,
        "max_power": 4.0,
    }

    description = get_model_description(config)

    assert description == "Connection 2.0kW to 4.0kW"


def test_connection_get_model_description_min_only() -> None:
    """Test connection model description with only min power."""
    config: connection.ConnectionConfigSchema = {
        "element_type": connection.ELEMENT_TYPE,
        "name": "Test Connection",
        "source": "source",
        "target": "target",
        "min_power": 2.0,
    }

    description = get_model_description(config)

    assert description == "Connection (min 2.0kW)"


def test_connection_get_model_description_max_only() -> None:
    """Test connection model description with only max power."""
    config: connection.ConnectionConfigSchema = {
        "element_type": connection.ELEMENT_TYPE,
        "name": "Test Connection",
        "source": "source",
        "target": "target",
        "max_power": 4.0,
    }

    description = get_model_description(config)

    assert description == "Connection (max 4.0kW)"


def test_connection_get_model_description_no_limits() -> None:
    """Test connection model description with no power limits."""
    config: connection.ConnectionConfigSchema = {
        "element_type": connection.ELEMENT_TYPE,
        "name": "Test Connection",
        "source": "source",
        "target": "target",
    }

    description = get_model_description(config)

    assert description == "Connection"


def test_photovoltaics_get_model_description() -> None:
    """Test photovoltaics model description generation."""
    config: photovoltaics.PhotovoltaicsConfigSchema = {
        "element_type": photovoltaics.ELEMENT_TYPE,
        "name": "Test PV",
        "forecast": ["sensor.solar_forecast"],
        "price_production": 0.12,
    }

    description = get_model_description(config)

    assert description == "Solar"


def test_constant_load_get_model_description() -> None:
    """Test constant load model description generation."""
    config: constant_load.ConstantLoadConfigSchema = {
        "element_type": constant_load.ELEMENT_TYPE,
        "name": "Test Load",
        "power": 2.5,
    }

    description = get_model_description(config)

    assert description == "Constant Load 2.5kW"


def test_forecast_load_get_model_description() -> None:
    """Test forecast load model description generation."""
    config: forecast_load.ForecastLoadConfigSchema = {
        "element_type": forecast_load.ELEMENT_TYPE,
        "name": "Test Forecast Load",
        "forecast": ["sensor.load_forecast"],
    }

    description = get_model_description(config)

    assert description == "Forecast Load"


def test_node_get_model_description() -> None:
    """Test node model description generation."""
    config: node.NodeConfigSchema = {
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
        get_model_description(cast("ElementConfigSchema", config))
