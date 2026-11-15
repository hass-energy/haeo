"""Tests for a battery without a capacity, which is an unbounded store."""

import numpy as np
import pytest

from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    BatteryElementConfig,
)
from custom_components.haeo.core.model.network import Network


@pytest.mark.parametrize(("min_charge", "expected"), [(None, -6.0), (-4.0, -4.0)])
def test_unbounded_store_falls_below_zero_to_its_min_charge(min_charge: float | None, expected: float) -> None:
    """Without a capacity, stored energy falls below zero, held only by a priced min charge."""
    network = Network(name="unbounded", periods=np.full(3, 1.0))
    config: BatteryElementConfig = {
        "element_type": MODEL_ELEMENT_TYPE_BATTERY,
        "name": "store",
        "capacity": None,
        "initial_charge": 0.0,
        "charge_limit_cost": 100.0,
    }
    if min_charge is not None:
        config["min_charge"] = min_charge
    store = network.add(config)
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "sink", "is_source": False})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "drain",
            "source": "store",
            "target": "sink",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 2.0},
                "pricing": {"segment_type": "pricing", "price": -1.0},
            },
        }
    )

    network.optimize()

    assert store.extract_values(store.stored_energy)[-1] == pytest.approx(expected)
