"""Tests for the deferrable load model element."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BUFFER,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    SegmentSpec,
)
from custom_components.haeo.core.model.elements.buffer import BUFFER_ENERGY_REQUIRED, BUFFER_ENERGY_SHORTFALL
from custom_components.haeo.core.model.elements.deferrable_load import DeferrableLoad, DeferrableLoadOutputName


def _opened_at_window_starts(in_window: list[float], window_start: list[float], due: list[float]) -> list[float]:
    """Open each due amount at the start of its window, as for one event per window."""
    opened = [0.0] * len(due)
    for end, amount in enumerate(due):
        if amount:
            start = end - 1
            while start > 0 and in_window[start - 1] and not window_start[start]:
                start -= 1
            opened[start] += amount
    return opened


def _build_network(
    *,
    in_window: list[float],
    window_start: list[float],
    due: list[float],
    opened: list[float] | None = None,
    deficit_price: np.ndarray | float = 10.0,
    initial_energy: float = 0.0,
    overage_price: np.ndarray | float = 0.0,
    supply_price: list[float] | None = None,
    max_supply_power: list[float] | None = None,
) -> tuple[Network, DeferrableLoad]:
    """Build a grid-fed deferrable load network with one-hour periods."""
    n = len(in_window)
    prices = supply_price if supply_price is not None else [0.1] * n
    network = Network(name="test_network", periods=np.array([1.0] * n))

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    load = network.add(
        {
            "element_type": "deferrable_load",
            "name": "load",
            "in_window": np.array(in_window),
            "window_start": np.array(window_start),
            "opened": np.array(
                opened if opened is not None else _opened_at_window_starts(in_window, window_start, due)
            ),
            "due": np.array(due),
            "deficit_price": np.broadcast_to(np.asarray(deficit_price, dtype=np.float64), n + 1).copy(),
            "initial_energy": initial_energy,
            "overage_price": np.broadcast_to(np.asarray(overage_price, dtype=np.float64), n + 1).copy(),
            "is_source": False,
            "is_sink": True,
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


def _outputs(load: DeferrableLoad, name: DeferrableLoadOutputName) -> np.ndarray:
    return np.array(load.outputs()[name].values)


def test_requirement_met_in_cheapest_period() -> None:
    """The load takes its requirement in the cheapest in-window period."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 5.0],
        supply_price=[0.2, 0.1],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 5.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 0.0, 5.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_shortfall"), [0.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(5.0 * 0.1)


def test_sequential_windows_settle_separately() -> None:
    """A missed first window is priced at its own end and the next window starts from zero."""
    # Window A covers period 0 (ends at boundary 1), window B covers periods
    # 2-3 (starts at boundary 2, ends at boundary 4). No supply in window A.
    network, load = _build_network(
        in_window=[1.0, 0.0, 1.0, 1.0],
        window_start=[1.0, 0.0, 1.0, 0.0, 0.0],
        due=[0.0, 3.0, 0.0, 0.0, 4.0],
        deficit_price=np.array([0.0, 5.0, 7.0, 7.0, 9.0]),
        max_supply_power=[0.0, 100.0, 100.0, 100.0],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_shortfall"), [0.0, 3.0, 0.0, 0.0, 0.0], atol=1e-9)
    delivered = _outputs(load, "deferrable_load_energy_delivered")
    assert delivered[2] == pytest.approx(0.0)
    assert delivered[4] == pytest.approx(4.0)
    # Window A's shortfall is priced at its own end boundary only.
    assert cost == pytest.approx(3.0 * 5.0 + 4.0 * 0.1)


def test_adjacent_windows_stay_separate() -> None:
    """A window starting where another ends resets the accumulator at that boundary."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 1.0, 0.0],
        due=[0.0, 2.0, 3.0],
        supply_price=[0.1, 0.1],
    )

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 2.0, 3.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [2.0, 3.0], atol=1e-9)


def test_window_open_at_horizon_end_settles_at_final_boundary() -> None:
    """A window still open at the horizon end is due at the final boundary, so early cheap energy is used."""
    network, load = _build_network(
        in_window=[0.0, 1.0, 1.0],
        window_start=[0.0, 1.0, 0.0, 0.0],
        due=[0.0, 0.0, 0.0, 4.0],
        supply_price=[0.1, 0.1, 0.5],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 4.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(4.0 * 0.1)


def test_unmeetable_requirement_prices_the_shortfall() -> None:
    """A physically unmeetable requirement is priced, not infeasible."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 8.0],
        deficit_price=5.0,
        supply_price=[0.1, 0.2],
        max_supply_power=[2.0, 2.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(4.0)
    assert _outputs(load, "deferrable_load_energy_shortfall")[-1] == pytest.approx(4.0)
    assert cost == pytest.approx(2.0 * 0.1 + 2.0 * 0.2 + 4.0 * 5.0)


def test_cheap_deficit_price_beats_expensive_energy() -> None:
    """When energy costs more than the deficit price, the load stays unmet."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        deficit_price=0.05,
        supply_price=[0.5, 0.5],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(4.0 * 0.05)


def test_power_is_zero_outside_windows() -> None:
    """Even free or rewarded energy is not absorbed outside windows."""
    network, load = _build_network(
        in_window=[0.0, 1.0, 0.0],
        window_start=[0.0, 1.0, 0.0, 0.0],
        due=[0.0, 0.0, 2.0, 0.0],
        overage_price=0.0,
        supply_price=[-1.0, 0.1, -1.0],
        max_supply_power=[10.0, 10.0, 10.0],
    )

    network.optimize()

    power = _outputs(load, "deferrable_load_power")
    assert power[0] == pytest.approx(0.0)
    assert power[2] == pytest.approx(0.0)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 0.0, 2.0, 0.0], atol=1e-9)


def test_free_overage_takes_energy_that_pays_to_be_used() -> None:
    """Delivery beyond the requirement is never forbidden; free overage takes energy that pays to be used."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        supply_price=[-0.2, -0.2],
        max_supply_power=[10.0, 10.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(20.0)
    # Overage is booked where delivery first runs beyond what has started
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 6.0, 10.0], atol=1e-9)
    assert cost == pytest.approx(-20.0 * 0.2)


def test_overage_price_allows_and_prices_extra_delivery() -> None:
    """With an overage price, extra delivery happens when worth it and is priced at the window end."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        overage_price=0.05,
        supply_price=[-0.2, -0.2],
        max_supply_power=[10.0, 10.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(20.0)
    # Overage is booked where delivery first runs beyond what has started
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 6.0, 10.0], atol=1e-9)
    assert cost == pytest.approx(-20.0 * 0.2 + 16.0 * 0.05)


def test_expensive_overage_is_avoided() -> None:
    """An overage price above the energy reward stops delivery at the requirement."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        overage_price=1.0,
        supply_price=[-0.2, -0.2],
        max_supply_power=[10.0, 10.0],
    )

    network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(4.0)


def test_initial_energy_seeds_only_the_open_window() -> None:
    """Energy already delivered counts toward the open window, not a later one."""
    network, load = _build_network(
        in_window=[1.0, 0.0, 1.0],
        window_start=[0.0, 0.0, 1.0, 0.0],
        due=[0.0, 5.0, 0.0, 5.0],
        initial_energy=2.0,
    )

    cost = network.optimize()

    delivered = _outputs(load, "deferrable_load_energy_delivered")
    np.testing.assert_allclose(delivered, [2.0, 5.0, 0.0, 5.0], atol=1e-9)
    assert cost == pytest.approx((3.0 + 5.0) * 0.1)


def test_initial_energy_ignored_without_an_open_window() -> None:
    """With no window open at the horizon start the accumulator starts from zero."""
    network, load = _build_network(
        in_window=[0.0, 1.0],
        window_start=[0.0, 1.0, 0.0],
        due=[0.0, 0.0, 3.0],
        initial_energy=2.0,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 0.0, 3.0], atol=1e-9)
    assert cost == pytest.approx(3.0 * 0.1)


def test_under_target_telemetry_leaves_the_remainder_due() -> None:
    """When telemetry is short of the requirement, the remainder stays due at the window end."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[0.0, 0.0, 0.0],
        due=[0.0, 0.0, 5.0],
        initial_energy=1.0,
        deficit_price=5.0,
        max_supply_power=[1.0, 1.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_shortfall")[-1] == pytest.approx(2.0)
    assert cost == pytest.approx(2.0 * 0.1 + 2.0 * 5.0)


@pytest.mark.parametrize("overage_price", [0.0, 1.0], ids=["free", "priced"])
def test_over_target_telemetry_stays_feasible(overage_price: float) -> None:
    """Telemetry beyond the requirement stays feasible and takes no new delivery; its overshoot is overage."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[0.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        initial_energy=6.0,
        overage_price=overage_price,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [6.0, 6.0, 6.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 2.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(2.0 * overage_price)


def test_over_target_telemetry_and_new_delivery_are_both_overage() -> None:
    """The telemetry overshoot and any new delivery beyond the requirement are priced alike."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[0.0, 0.0, 0.0],
        due=[0.0, 0.0, 4.0],
        initial_energy=6.0,
        overage_price=0.05,
        supply_price=[-0.2, -0.2],
        max_supply_power=[1.0, 1.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(8.0)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 3.0, 1.0], atol=1e-9)
    assert cost == pytest.approx(-2.0 * 0.2 + 4.0 * 0.05)


# Two 2-hour events overlapping by an hour: A covers periods 0-1 and B periods 1-2, 2 kWh each.
_OVERLAPPING_IN_WINDOW = [1.0, 1.0, 1.0]
_OVERLAPPING_WINDOW_START = [1.0, 0.0, 0.0, 0.0]
_OVERLAPPING_OPENED = [2.0, 2.0, 0.0, 0.0]
_OVERLAPPING_DUE = [0.0, 0.0, 2.0, 2.0]


def _overlapping(
    *, supply_price: list[float], max_supply_power: list[float], overage_price: float = 0.0
) -> tuple[Network, DeferrableLoad]:
    """Build the two overlapping events with the given supply."""
    return _build_network(
        in_window=_OVERLAPPING_IN_WINDOW,
        window_start=_OVERLAPPING_WINDOW_START,
        opened=_OVERLAPPING_OPENED,
        due=_OVERLAPPING_DUE,
        overage_price=overage_price,
        supply_price=supply_price,
        max_supply_power=max_supply_power,
    )


def test_overlapping_events_each_take_energy_in_their_own_window() -> None:
    """The cheap first hour serves only the event open then; the later event's energy lands in its own window."""
    network, load = _overlapping(supply_price=[0.01, 0.1, 0.2], max_supply_power=[10.0] * 3)

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [2.0, 2.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0] * 4, atol=1e-9)
    assert cost == pytest.approx(2.0 * 0.01 + 2.0 * 0.1)


def test_energy_before_an_event_starts_never_counts_toward_it() -> None:
    """Energy delivered before the later event starts is overage, even when it pays to take it."""
    network, load = _overlapping(overage_price=0.05, supply_price=[-0.1, 0.1, 0.2], max_supply_power=[10.0] * 3)

    network.optimize()

    power = _outputs(load, "deferrable_load_power")
    np.testing.assert_allclose(power, [10.0, 2.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 8.0, 0.0, 0.0], atol=1e-9)


def test_a_missed_deadline_stays_missed() -> None:
    """Energy arriving after an event ends cannot make up its shortfall; it only serves the later event."""
    network, load = _overlapping(supply_price=[0.1, 0.1, 0.2], max_supply_power=[0.0, 0.0, 10.0])

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_shortfall"), [0.0, 0.0, 2.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 0.0, 2.0], atol=1e-9)
    assert cost == pytest.approx(2.0 * 0.2 + 2.0 * 10.0)


def test_shortfall_cannot_be_booked_where_nothing_is_due() -> None:
    """A free boundary between two deadlines cannot hold shortfall that a later, priced miss would hide behind."""
    network, load = _build_network(
        in_window=[1.0, 1.0, 1.0, 1.0],
        window_start=[1.0, 0.0, 0.0, 0.0, 0.0],
        opened=[6.0, 0.0, 0.0, 0.0, 0.0],
        due=[0.0, 0.0, 2.0, 0.0, 4.0],
        deficit_price=np.array([0.0, 0.0, 10.0, 0.0, 10.0]),
        supply_price=[0.1, 0.1, 5.0, 5.0],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_shortfall"), [0.0] * 5, atol=1e-9)
    assert cost == pytest.approx(6.0 * 0.1)


def test_overage_cannot_be_booked_early_at_a_free_boundary() -> None:
    """Overage is priced at its window's end, so booking it at an earlier free boundary avoids nothing."""
    network, load = _build_network(
        in_window=[1.0, 1.0, 1.0, 1.0],
        window_start=[1.0, 0.0, 0.0, 0.0, 0.0],
        opened=[5.0, 0.0, 0.0, 0.0, 0.0],
        due=[0.0, 0.0, 0.0, 0.0, 5.0],
        overage_price=np.array([0.0, 0.0, 0.0, 0.0, 0.6]),
        supply_price=[-0.1, 0.01, 0.01, -0.5],
        max_supply_power=[10.0] * 4,
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(5.0)
    assert cost == pytest.approx(-5.0 * 0.5)


def test_window_changes_update_reactively() -> None:
    """Moving a window only changes parameters and re-optimizes correctly."""
    network, load = _build_network(
        in_window=[1.0, 0.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 2.0, 0.0],
        supply_price=[0.1, 0.3],
    )
    assert network.optimize() == pytest.approx(2.0 * 0.1)

    load["in_window"] = np.array([0.0, 1.0])
    load["window_start"] = np.array([0.0, 1.0, 0.0])
    load["opened"] = np.array([0.0, 2.0, 0.0])
    load["due"] = np.array([0.0, 0.0, 2.0])

    assert network.optimize() == pytest.approx(2.0 * 0.3)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 2.0], atol=1e-9)


def test_outputs_present() -> None:
    """The element exposes power, delivered, shortfall, overage and shadow price outputs."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        due=[0.0, 0.0, 5.0],
    )
    network.optimize()

    outputs = load.outputs()
    assert len(outputs["deferrable_load_power"].values) == 2
    for name in (
        "deferrable_load_energy_delivered",
        "deferrable_load_energy_shortfall",
        "deferrable_load_energy_overage",
    ):
        assert len(outputs[name].values) == 3
    assert "deferrable_load_requirement" in outputs


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
