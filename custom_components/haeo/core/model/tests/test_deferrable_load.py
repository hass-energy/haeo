"""Tests for the deferrable load model element."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    SegmentSpec,
)
from custom_components.haeo.core.model.elements.deferrable_load import DeferrableLoad


def _build_network(
    *,
    capacity: np.ndarray | float,
    required: np.ndarray | float,
    deficit_price: np.ndarray | float = 10.0,
    initial_energy: float = 0.0,
    overage_price: float = 0.0,
    supply_price: list[float] | None = None,
    max_supply_power: list[float] | None = None,
) -> tuple[Network, DeferrableLoad]:
    """Build a grid-fed deferrable load network."""
    prices = supply_price if supply_price is not None else [0.1, 0.2]
    n = len(prices)
    network = Network(name="test_network", periods=np.array([1.0] * n))

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    load = network.add(
        {
            "element_type": "deferrable_load",
            "name": "load",
            "capacity": capacity,
            "required": required,
            "deficit_price": deficit_price,
            "initial_energy": initial_energy,
            "overage_price": overage_price,
        }
    )
    segments: dict[str, SegmentSpec] = {
        "pricing": {"segment_type": "pricing", "price": np.array(prices)},
    }
    if max_supply_power is not None:
        segments["power_limit"] = {"segment_type": "power_limit", "max_power": np.array(max_supply_power)}
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "grid_to_load",
            "source": "grid",
            "target": "load",
            "tags": {1},
            "segments": segments,
        }
    )
    return network, load


def test_requirement_met_in_cheapest_period() -> None:
    """The load absorbs its requirement when energy is cheapest."""
    network, load = _build_network(
        capacity=np.array([5.0, 5.0, 5.0]),
        required=np.array([0.0, 0.0, 5.0]),
    )

    cost = network.optimize()

    absorbed = load.extract_values(load.energy)
    np.testing.assert_allclose(absorbed, [0.0, 5.0, 5.0])
    deficit = load.extract_values(load.deficit)
    np.testing.assert_allclose(deficit, [0.0, 0.0, 0.0])
    assert cost == pytest.approx(5.0 * 0.1)


def test_unmeetable_requirement_prices_the_deficit() -> None:
    """A physically unmeetable requirement is priced, not infeasible."""
    network, load = _build_network(
        capacity=np.array([8.0, 8.0, 8.0]),
        required=np.array([0.0, 0.0, 8.0]),
        deficit_price=5.0,
        max_supply_power=[2.0, 2.0],
    )

    cost = network.optimize()

    absorbed = load.extract_values(load.energy)
    assert absorbed[-1] == pytest.approx(4.0)  # 2 kW x 2 h is all the supply allows
    deficit = load.extract_values(load.deficit)
    assert deficit[-1] == pytest.approx(4.0)
    # Absorbing at both period prices plus the priced shortfall.
    assert cost == pytest.approx(2.0 * 0.1 + 2.0 * 0.2 + 4.0 * 5.0)


def test_deficit_stays_locked_in_after_deadline() -> None:
    """A missed deadline stays priced even if capacity later allows catch-up."""
    network, load = _build_network(
        capacity=np.array([3.0, 3.0, 6.0]),
        required=np.array([0.0, 3.0, 3.0]),
        deficit_price=5.0,
        supply_price=[0.1, 0.1],
        max_supply_power=[0.0, 100.0],  # nothing available before the first deadline
    )

    network.optimize()

    deficit = load.extract_values(load.deficit)
    assert deficit[1] == pytest.approx(3.0)
    # The shortfall persists at the horizon end even though absorption resumed.
    assert deficit[-1] == pytest.approx(3.0)


def test_cheap_deficit_price_beats_expensive_energy() -> None:
    """When energy costs more than the deficit price, the load stays unmet."""
    network, load = _build_network(
        capacity=np.array([4.0, 4.0, 4.0]),
        required=np.array([0.0, 0.0, 4.0]),
        deficit_price=0.05,
        supply_price=[0.5, 0.5],
    )

    cost = network.optimize()

    absorbed = load.extract_values(load.energy)
    np.testing.assert_allclose(absorbed, [0.0, 0.0, 0.0])
    assert cost == pytest.approx(4.0 * 0.05)


def test_initial_energy_counts_toward_requirement() -> None:
    """Energy already absorbed before the horizon reduces what must flow."""
    network, load = _build_network(
        capacity=np.array([5.0, 5.0, 5.0]),
        required=np.array([0.0, 0.0, 5.0]),
        initial_energy=2.0,
    )

    cost = network.optimize()

    absorbed = load.extract_values(load.energy)
    assert absorbed[0] == pytest.approx(2.0)
    assert absorbed[-1] == pytest.approx(5.0)
    assert cost == pytest.approx(3.0 * 0.1)


def test_overage_is_priced() -> None:
    """Absorbing beyond the requirement costs the overage price."""
    network, load = _build_network(
        capacity=np.array([10.0, 10.0, 10.0]),
        required=np.array([0.0, 0.0, 4.0]),
        # Negative supply price would reward unlimited absorption; the
        # overage price caps the free lunch at the requirement.
        supply_price=[-0.2, -0.2],
        overage_price=1.0,
    )

    network.optimize()

    absorbed = load.extract_values(load.energy)
    # Requirement is worth absorbing at negative price, overage is not
    # (1.0 overage price outweighs the 0.2 reward).
    assert absorbed[-1] == pytest.approx(4.0)


def test_outputs_present() -> None:
    """The element exposes power, absorbed, and deficit outputs."""
    network, load = _build_network(
        capacity=np.array([5.0, 5.0, 5.0]),
        required=np.array([0.0, 0.0, 5.0]),
    )
    network.optimize()

    outputs = load.outputs()
    assert outputs["deferrable_load_energy_absorbed"].values[-1] == pytest.approx(5.0)
    assert outputs["deferrable_load_energy_deficit"].values[-1] == pytest.approx(0.0)
    assert len(outputs["deferrable_load_power"].values) == 2


def test_initial_energy_beyond_capacity_stays_feasible() -> None:
    """Telemetry reporting more absorbed than planned must not crash the model."""
    network, load = _build_network(
        capacity=np.array([3.0, 3.0, 3.0]),
        required=np.array([0.0, 0.0, 3.0]),
        initial_energy=5.0,  # the car drove further than the schedule planned
    )

    cost = network.optimize()

    absorbed = load.extract_values(load.energy)
    assert absorbed[0] == pytest.approx(5.0)
    deficit = load.extract_values(load.deficit)
    np.testing.assert_allclose(deficit, [0.0, 0.0, 0.0])
    assert cost == pytest.approx(0.0)


def test_initial_overshoot_is_not_priced_as_overage() -> None:
    """An initial overshoot is a fact from telemetry, not priced overage."""
    network, _load = _build_network(
        capacity=np.array([4.0, 4.0, 4.0]),
        required=np.array([0.0, 0.0, 4.0]),
        initial_energy=6.0,
        overage_price=100.0,
    )

    cost = network.optimize()

    assert cost == pytest.approx(0.0)


def test_shortfall_priced_at_the_boundary_where_it_falls_due() -> None:
    """A cheaper price before the requirement falls due cannot absorb the shortfall."""
    network, load = _build_network(
        capacity=np.array([4.0, 4.0, 4.0]),
        required=np.array([0.0, 0.0, 4.0]),
        deficit_price=np.array([0.0, 0.1, 5.0]),
        max_supply_power=[0.0, 0.0],
    )

    cost = network.optimize()

    deficit = load.extract_values(load.deficit)
    np.testing.assert_allclose(deficit, [0.0, 0.0, 4.0])
    assert cost == pytest.approx(4.0 * 5.0)


def test_shortfall_cannot_be_booked_where_nothing_falls_due() -> None:
    """A boundary with no newly due requirement never carries a deficit increment."""
    # Two kWh fall due at boundary 1 and two more at boundary 3. Supply is
    # only available in the first period, so the second tranche is missed;
    # the cheap price at boundary 2 must not absorb that shortfall.
    network, load = _build_network(
        capacity=np.array([4.0, 4.0, 4.0, 4.0]),
        required=np.array([0.0, 2.0, 2.0, 4.0]),
        deficit_price=np.array([0.0, 5.0, 0.1, 5.0]),
        supply_price=[0.1, 0.1, 0.1],
        max_supply_power=[2.0, 0.0, 0.0],
    )

    cost = network.optimize()

    deficit = load.extract_values(load.deficit)
    assert deficit[2] - deficit[1] == pytest.approx(0.0)
    assert deficit[-1] == pytest.approx(2.0)
    assert cost == pytest.approx(2.0 * 0.1 + 2.0 * 5.0)


def test_negative_deficit_price_stays_bounded() -> None:
    """A negative deficit price cannot book more deficit than falls due."""
    network, load = _build_network(
        capacity=np.array([4.0, 4.0, 4.0]),
        required=np.array([0.0, 0.0, 4.0]),
        deficit_price=-1.0,
    )

    cost = network.optimize()

    deficit = load.extract_values(load.deficit)
    np.testing.assert_allclose(deficit, [0.0, 0.0, 4.0])
    assert cost == pytest.approx(-4.0)


def test_negative_overage_price_stays_bounded() -> None:
    """A negative overage price cannot claim more overage than capacity allows."""
    network, load = _build_network(
        capacity=np.array([10.0, 10.0, 10.0]),
        required=np.array([0.0, 0.0, 4.0]),
        overage_price=-1.0,
    )

    network.optimize()

    assert load.extract_values(load.overage)[0] <= 6.0 + 1e-9
