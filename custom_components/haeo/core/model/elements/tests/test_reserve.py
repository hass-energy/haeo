"""Tests for the reserve model element's window layout and network wiring."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    MODEL_ELEMENT_TYPE_RESERVE,
    ReserveElementConfig,
)
from custom_components.haeo.core.model.elements.reserve import ReserveKind, window_layout


@pytest.mark.parametrize(
    ("periods", "window", "block", "last", "fraction"),
    [
        pytest.param([1, 1, 1, 1], 2.0, [0, 0, 1, 1, 2], [2, 3, 4, 4, 4], [0, 0, 0, 0, 0], id="whole_periods"),
        pytest.param(
            [0.5, 1, 1.5, 1],
            1.25,
            [0, 0, 1, 2, 3],
            [1, 2, 2, 4, 4],
            [0.75, 1 / 6, 5 / 6, 0, 0],
            id="window_ends_inside_periods",
        ),
        pytest.param([1, 1], 5.0, [0, 0, 0], [2, 2, 2], [0, 0, 0], id="window_longer_than_horizon"),
        pytest.param([1, 1, 1], 0.5, [0, 2, 4, 6], [0, 1, 2, 3], [0.5, 0.5, 0.5, 0], id="window_shorter_than_periods"),
    ],
)
def test_window_layout(
    periods: list[float], window: float, block: list[int], last: list[int], fraction: list[float]
) -> None:
    """Each boundary's window ends at its last boundary plus a fraction of the next period."""
    layout = window_layout(np.asarray(periods, dtype=float), window)

    assert layout.block.tolist() == block
    assert layout.last.tolist() == last
    np.testing.assert_allclose(layout.fraction, fraction)


def _network(*, discharge_connections: int) -> Network:
    """Return a network with a house and a battery with the given number of discharge connections."""
    network = Network(name="test", periods=np.ones(2))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "bus", "is_source": False, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "house", "is_source": False, "is_sink": True})
    network.add(
        {"element_type": MODEL_ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10.0, "initial_charge": 5.0}
    )
    for index in range(discharge_connections):
        network.add(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"battery:discharge{index}",
                "source": "battery",
                "target": "bus",
                "tags": {0},
                "segments": {},
            }
        )
    return network


def _reserve(
    *, loads: list[str], storage: list[str], generation: list[str] | None = None, kind: ReserveKind = "reserve"
) -> ReserveElementConfig:
    return {
        "element_type": MODEL_ELEMENT_TYPE_RESERVE,
        "name": "reserve",
        "kind": kind,
        "loads": loads,
        "generation": generation or [],
        "storage": storage,
        "window": 1.0,
        "minimum": 0.0,
        "price": 1.0,
    }


@pytest.mark.parametrize(
    ("discharge_connections", "config", "error", "match"),
    [
        pytest.param(1, _reserve(loads=["missing"], storage=["battery"]), TypeError, "unknown element", id="unknown"),
        pytest.param(1, _reserve(loads=["house"], storage=["house"]), TypeError, "not a battery", id="not_battery"),
        pytest.param(0, _reserve(loads=["house"], storage=["battery"]), ValueError, "exactly one", id="no_discharge"),
        pytest.param(2, _reserve(loads=["house"], storage=["battery"]), ValueError, "exactly one", id="two_discharges"),
        pytest.param(
            1,
            _reserve(loads=["house"], storage=["battery"], kind="headroom"),
            ValueError,
            "charge through exactly one",
            id="headroom_without_charge",
        ),
        pytest.param(
            1,
            _reserve(loads=[], generation=["house"], storage=["battery"]),
            ValueError,
            "limit on the power it produces",
            id="generation_without_limit",
        ),
    ],
)
def test_reserve_rejects_references_it_cannot_resolve(
    discharge_connections: int, config: ReserveElementConfig, error: type[Exception], match: str
) -> None:
    """A reserve covers network elements and is held by batteries that discharge through one connection."""
    network = _network(discharge_connections=discharge_connections)

    with pytest.raises(error, match=match):
        network.add(config)
