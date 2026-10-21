"""Tests for connection adapter availability checks."""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.connection import CONNECTION_DEVICE_CONNECTION, CONNECTION_POWER
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.grid import GRID_DEVICE_GRID, GRID_POWER_EXPORT
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData

from .conftest import bus_node, grid_at, optimize_participants


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
