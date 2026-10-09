"""Tests for connection adapter availability checks."""

from homeassistant.core import HomeAssistant
import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.connection import CONNECTION_DEVICE_CONNECTION, CONNECTION_POWER
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.grid import GRID_DEVICE_GRID, GRID_POWER_EXPORT
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType, connection
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData
from custom_components.haeo.elements.availability import schema_config_available

from .conftest import bus_node, grid_at, optimize_participants


def _set_sensor(hass: HomeAssistant, entity_id: str, value: str, unit: str = "kW") -> None:
    """Set a sensor state in hass."""
    hass.states.async_set(entity_id, value, {"unit_of_measurement": unit})


async def test_available_returns_true_with_no_optional_fields(hass: HomeAssistant) -> None:
    """Connection available() should return True with only required fields."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {},
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_true_when_optional_sensors_exist(hass: HomeAssistant) -> None:
    """Connection available() should return True when all configured sensors exist."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    _set_sensor(hass, "sensor.max_power_ts", "3.0", "kW")
    _set_sensor(hass, "sensor.eff_st", "95.0", "%")
    _set_sensor(hass, "sensor.eff_ts", "90.0", "%")
    _set_sensor(hass, "sensor.price_st", "0.10", "$/kWh")
    _set_sensor(hass, "sensor.price_ts", "0.05", "$/kWh")

    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_power_st"]),
            "max_power_target_source": as_entity_value(["sensor.max_power_ts"]),
        },
        connection.SECTION_PRICING: {
            "price_source_target": as_entity_value(["sensor.price_st"]),
            "price_target_source": as_entity_value(["sensor.price_ts"]),
        },
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_entity_value(["sensor.eff_st"]),
            "efficiency_target_source": as_entity_value(["sensor.eff_ts"]),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


async def test_available_returns_false_when_optional_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when a configured optional sensor is missing."""
    _set_sensor(hass, "sensor.max_power_st", "5.0", "kW")
    # max_power_ts sensor is missing

    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_entity_value(["sensor.max_power_st"]),
            "max_power_target_source": as_entity_value(["sensor.missing"]),
        },
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {},
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_false_when_efficiency_sensor_missing(hass: HomeAssistant) -> None:
    """Connection available() should return False when efficiency sensor is missing."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {},
        connection.SECTION_PRICING: {},
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_entity_value(["sensor.missing"]),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is False


async def test_available_returns_true_with_constant_values(hass: HomeAssistant) -> None:
    """Connection available() should return True when values are constants."""
    config: connection.ConnectionConfigSchema = {
        "element_type": ElementType.CONNECTION,
        "name": "c1",
        connection.SECTION_ENDPOINTS: {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        connection.SECTION_POWER_LIMITS: {
            "max_power_source_target": as_constant_value(5.0),
            "max_power_target_source": as_constant_value(4.0),
        },
        connection.SECTION_PRICING: {
            "price_source_target": as_constant_value(0.1),
            "price_target_source": as_constant_value(0.2),
        },
        connection.SECTION_EFFICIENCY: {
            "efficiency_source_target": as_constant_value(0.9),
            "efficiency_target_source": as_constant_value(0.91),
        },
    }

    result = schema_config_available(config, sm=hass.states)
    assert result is True


def test_connection_limit_binds_where_power_is_reported() -> None:
    """A connection at its limit reports the limit, with the efficiency loss after it.

    Importing at bus a and exporting at bus b is profitable, so the optimizer runs the
    connection at its limit. The connection power sensor reads the limit and bus b
    receives the limit times the efficiency.
    """
    efficiency = 0.9
    cap = 5.0
    link = ConnectionConfigData(
        element_type=ElementType.CONNECTION,
        name="link",
        endpoints={"source": as_connection_target("a"), "target": as_connection_target("b")},
        power_limits={"max_power_source_target": np.array([cap])},
        efficiency={"efficiency_source_target": np.array([efficiency])},
        pricing={"price_source_target": np.array([0.01])},
    )
    market = grid_at("market", "b", import_price=10.0, export_price=1.0)
    model_outputs = optimize_participants(
        {
            "a": bus_node("a"),
            "b": bus_node("b"),
            "link": link,
            "supply": grid_at("supply", "a", import_price=0.1, export_price=0.0),
            "market": market,
        }
    )

    outputs = connection_adapter.outputs("link", model_outputs)[CONNECTION_DEVICE_CONNECTION]

    assert outputs[CONNECTION_POWER].values[0] == pytest.approx(cap)
    market_outputs = grid_adapter.outputs("market", model_outputs, config=market, periods=np.array([1.0]))
    assert market_outputs[GRID_DEVICE_GRID][GRID_POWER_EXPORT].values[0] == pytest.approx(cap * efficiency)
