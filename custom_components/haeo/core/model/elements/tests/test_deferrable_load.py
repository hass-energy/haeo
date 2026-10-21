"""Tests for the deferrable load model element in a network: reactive updates and buffers that cover it.

Single-element behavior is covered by the cases in ``core/model/tests/test_data/deferrable_load.py``.
"""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BUFFER,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.core.model.elements.buffer import BUFFER_ENERGY_REQUIRED, BUFFER_ENERGY_SHORTFALL
from custom_components.haeo.core.model.elements.deferrable_load import DeferrableLoad, DeferrableLoadOutputName


def _outputs(load: DeferrableLoad, name: DeferrableLoadOutputName) -> np.ndarray:
    return np.array(load.outputs()[name].values)


def test_window_changes_update_reactively() -> None:
    """Moving a window only changes parameters and re-optimizes correctly."""
    network = Network(name="test_network", periods=np.ones(2))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    load = network.add(
        {
            "element_type": "deferrable_load",
            "name": "load",
            "in_window": np.array([1.0, 0.0]),
            "window_start": np.array([1.0, 0.0, 0.0]),
            "opened": np.array([2.0, 0.0, 0.0]),
            "due": np.array([0.0, 2.0, 0.0]),
            "deficit_price": np.full(3, 10.0),
            "overage_price": np.zeros(3),
            "is_source": False,
            "is_sink": True,
        }
    )
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid_to_load",
            "source": "grid",
            "target": "load",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.array([0.1, 0.3])}},
        }
    )
    assert network.optimize() == pytest.approx(2.0 * 0.1)

    load["in_window"] = np.array([0.0, 1.0])
    load["window_start"] = np.array([0.0, 1.0, 0.0])
    load["opened"] = np.array([0.0, 2.0, 0.0])
    load["due"] = np.array([0.0, 0.0, 2.0])

    assert network.optimize() == pytest.approx(2.0 * 0.3)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 2.0], atol=1e-9)


def _reserve_network() -> tuple[Network, DeferrableLoad]:
    """Build a grid-fed deferrable load due in periods 1-3 beside a 2 kWh battery that only backs a reserve."""
    network = Network(name="test_network", periods=np.array([1.0] * 4))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "bus", "is_source": False, "is_sink": False})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid:import",
            "source": "grid",
            "target": "bus",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.array([0.2, 0.1, 0.2, 0.2])}},
        }
    )
    # The battery holds its 2 kWh: it has no connections, so it only backs the reserve.
    network.add(
        {
            "element_type": "battery",
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 2.0,
            "charge_limit_cost": 100.0,
        }
    )
    load = network.add(
        {
            "element_type": "deferrable_load",
            "name": "load",
            "in_window": np.array([0.0, 1.0, 1.0, 1.0]),
            "window_start": np.array([0.0, 1.0, 0.0, 0.0, 0.0]),
            "opened": np.array([0.0, 3.0, 0.0, 0.0, 0.0]),
            "due": np.array([0.0, 0.0, 0.0, 0.0, 3.0]),
            "deficit_price": np.full(5, 10.0),
            "overage_price": np.zeros(5),
            "is_source": False,
            "is_sink": True,
        }
    )
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "bus:load",
            "source": "bus",
            "target": "load",
            "tags": {1},
        }
    )
    return network, load


def test_unbuffered_deferrable_load_takes_the_cheapest_period() -> None:
    """Without a reserve the whole requirement takes the cheapest period."""
    network, load = _reserve_network()

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 3.0, 0.0, 0.0], atol=1e-9)


def test_reserve_buffer_counts_the_planned_load() -> None:
    """A reserve buffer counts a deferrable load by its planned power, so the plan spreads it to keep the reserve."""
    network, load = _reserve_network()
    buffer = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_BUFFER,
            "name": "buffer",
            "kind": "reserve",
            "loads": ["load"],
            "generation": [],
            "storage": ["battery"],
            "window": 1.0,
            "level": None,
            "price": 50.0,
        }
    )

    network.optimize()

    power = _outputs(load, "deferrable_load_power")
    assert power.sum() == pytest.approx(3.0)
    # The 2 kWh battery covers at most 2 kWh of the next hour's planned load, so no hour plans more.
    assert power.max() <= 2.0 + 1e-9
    required = np.asarray(buffer.outputs()[BUFFER_ENERGY_REQUIRED].values)
    np.testing.assert_allclose(required[1:4], power[1:], atol=1e-9)
    np.testing.assert_allclose(buffer.outputs()[BUFFER_ENERGY_SHORTFALL].values, [0.0] * 5, atol=1e-9)
