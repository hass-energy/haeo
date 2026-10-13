"""Tests for the HoldingCost model element."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_HOLDING_COST as ELEMENT_TYPE_HOLDING_COST
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.holding_cost import HoldingCostDirection


def _discharging_network() -> Network:
    """Return a battery holding 5 kWh that earns 1 per kWh discharged, at up to 3 kW, over two 1 hour periods."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10.0, "initial_charge": 5.0})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "discharge",
            "source": "battery",
            "target": "sink",
            "tags": {0},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0, 3.0])},
                "pricing": {"segment_type": "pricing", "price": np.array([-1.0, -1.0])},
            },
        }
    )
    return network


def _charging_network() -> Network:
    """Return a battery holding 2 kWh, worth 1 per kWh at the end, charged for free at up to 3 kW."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add(
        {
            "element_type": ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 2.0,
            "salvage_value": 1.0,
        }
    )
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "charge",
            "source": "source",
            "target": "battery",
            "tags": {0},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0, 3.0])},
            },
        }
    )
    return network


def _add_holding_cost(network: Network, direction: HoldingCostDirection, price: float) -> None:
    network.add(
        {
            "element_type": ELEMENT_TYPE_HOLDING_COST,
            "name": "battery:holding_cost",
            "storage": "battery",
            "direction": direction,
            "threshold": 4.0,
            "price": price,
        }
    )


def _stored_energy(network: Network) -> list[float]:
    return list(network.elements["battery"].outputs()["battery_energy_stored"].values)


def test_holding_cost_below_threshold_delays_discharge() -> None:
    """Energy below the threshold is only used once it no longer has to stay below for long.

    Holding a kWh below 4 kWh costs 0.75 per hour. A kWh discharged in the first period stays
    below for two hours (1.5, more than it earns), but one discharged in the second period
    stays below for one hour (0.75, less than it earns).
    """
    network = _discharging_network()
    _add_holding_cost(network, "below", 0.75)

    assert network.optimize() == pytest.approx(-4.0 + 0.75 * 3.0)
    assert _stored_energy(network) == pytest.approx([5.0, 4.0, 1.0])


def test_holding_cost_above_threshold_delays_charge() -> None:
    """Energy above the threshold is only stored once it no longer has to stay above for long."""
    network = _charging_network()
    _add_holding_cost(network, "above", 0.75)

    assert network.optimize() == pytest.approx(-7.0 + 0.75 * 3.0)
    assert _stored_energy(network) == pytest.approx([2.0, 4.0, 7.0])


def test_holding_cost_price_update_reoptimizes() -> None:
    """Updating the price of a holding cost changes the next optimization."""
    network = _discharging_network()
    _add_holding_cost(network, "below", 0.75)
    network.optimize()

    network.elements["battery:holding_cost"]["price"] = np.array([0.0, 0.0])

    assert network.optimize() == pytest.approx(-5.0)
    assert _stored_energy(network) == pytest.approx([5.0, 2.0, 0.0])


def test_add_holding_cost_unknown_battery() -> None:
    """Adding a holding cost that references a missing battery raises TypeError."""
    network = Network(name="test", periods=np.array([1.0]))
    with pytest.raises(TypeError, match="references unknown battery 'missing'"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_HOLDING_COST,
                "name": "cost",
                "storage": "missing",
                "direction": "below",
                "threshold": 1.0,
                "price": 0.1,
            }
        )
