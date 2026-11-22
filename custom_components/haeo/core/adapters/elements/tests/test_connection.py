"""Tests for how a connection's segments shape the power through it in the optimization."""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.elements.connection import CONNECTION_DEVICE_CONNECTION, CONNECTION_POWER
from custom_components.haeo.core.adapters.elements.connection import adapter as connection_adapter
from custom_components.haeo.core.adapters.elements.grid import GRID_DEVICE_GRID, GRID_POWER_EXPORT
from custom_components.haeo.core.adapters.elements.grid import adapter as grid_adapter
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData, SegmentData

from .conftest import bus_node, grid_at, optimize_participants

CAP = 5.0
EFFICIENCY = 0.9


@pytest.mark.parametrize(
    ("segments", "exported"),
    [
        pytest.param(
            [
                {"segment_type": "power_limit", "max_power": np.array([CAP])},
                {"segment_type": "pricing", "price": np.array([0.01])},
                {"segment_type": "efficiency", "efficiency": np.array([EFFICIENCY])},
            ],
            CAP * EFFICIENCY,
            id="limit_before_losses",
        ),
        pytest.param(
            [
                {"segment_type": "efficiency", "efficiency": np.array([EFFICIENCY])},
                {"segment_type": "pricing", "price": np.array([0.01])},
                {"segment_type": "power_limit", "max_power": np.array([CAP])},
            ],
            CAP,
            id="limit_after_losses",
        ),
    ],
)
def test_connection_applies_its_segments_in_order(segments: list[SegmentData], exported: float) -> None:
    """A connection at its limit reports the limit, and its losses apply where they sit in the order.

    Importing at bus a and exporting at bus b is profitable, so the optimizer runs the
    connection at its limit. The connection power sensor reads the power entering the
    limit, and bus b receives what is left after every segment.
    """
    link = ConnectionConfigData(
        element_type=ElementType.CONNECTION,
        name="link",
        endpoints={"source": as_connection_target("a"), "target": as_connection_target("b")},
        segments=segments,
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

    assert outputs[CONNECTION_POWER].values[0] == pytest.approx(CAP)
    market_outputs = grid_adapter.outputs("market", model_outputs, config=market, periods=np.array([1.0]))
    assert market_outputs[GRID_DEVICE_GRID][GRID_POWER_EXPORT].values[0] == pytest.approx(exported)
