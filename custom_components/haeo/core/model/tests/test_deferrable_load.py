"""Tests for the deferrable load model element."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    SegmentSpec,
)
from custom_components.haeo.core.model.elements.deferrable_load import DeferrableLoad, DeferrableLoadOutputName


def _build_network(
    *,
    in_window: list[float],
    window_start: list[float],
    requirement: list[float],
    deficit_price: np.ndarray | float = 10.0,
    initial_energy: float = 0.0,
    overage_price: np.ndarray | float | None = None,
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
            "requirement": np.array(requirement),
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


def _outputs(load: DeferrableLoad, name: DeferrableLoadOutputName) -> np.ndarray:
    return np.array(load.outputs()[name].values)


def test_requirement_met_in_cheapest_period() -> None:
    """The load takes its requirement in the cheapest in-window period."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 5.0],
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
        requirement=[0.0, 3.0, 0.0, 0.0, 4.0],
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
        requirement=[0.0, 2.0, 3.0],
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
        requirement=[0.0, 0.0, 0.0, 4.0],
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
        requirement=[0.0, 0.0, 8.0],
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
        requirement=[0.0, 0.0, 4.0],
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
        requirement=[0.0, 0.0, 2.0, 0.0],
        overage_price=0.0,
        supply_price=[-1.0, 0.1, -1.0],
        max_supply_power=[10.0, 10.0, 10.0],
    )

    network.optimize()

    power = _outputs(load, "deferrable_load_power")
    assert power[0] == pytest.approx(0.0)
    assert power[2] == pytest.approx(0.0)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [0.0, 0.0, 2.0, 0.0], atol=1e-9)


def test_without_overage_price_delivery_is_capped() -> None:
    """With no overage price the requirement is a hard cap, even when energy pays to be used."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        supply_price=[-0.2, -0.2],
        max_supply_power=[10.0, 10.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(4.0)
    assert cost == pytest.approx(-4.0 * 0.2)


def test_overage_price_allows_and_prices_extra_delivery() -> None:
    """With an overage price, extra delivery happens when worth it and is priced at the window end."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        overage_price=0.05,
        supply_price=[-0.2, -0.2],
        max_supply_power=[10.0, 10.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(20.0)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 0.0, 16.0], atol=1e-9)
    assert cost == pytest.approx(-20.0 * 0.2 + 16.0 * 0.05)


def test_expensive_overage_is_avoided() -> None:
    """An overage price above the energy reward stops delivery at the requirement."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
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
        requirement=[0.0, 5.0, 0.0, 5.0],
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
        requirement=[0.0, 0.0, 3.0],
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
        requirement=[0.0, 0.0, 5.0],
        initial_energy=1.0,
        deficit_price=5.0,
        max_supply_power=[1.0, 1.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_shortfall")[-1] == pytest.approx(2.0)
    assert cost == pytest.approx(2.0 * 0.1 + 2.0 * 5.0)


@pytest.mark.parametrize("overage_price", [None, 1.0], ids=["capped", "priced"])
def test_over_target_telemetry_is_sunk(overage_price: float | None) -> None:
    """Telemetry beyond the requirement stays feasible, takes no new delivery, and is not priced."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[0.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        initial_energy=6.0,
        overage_price=overage_price,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_delivered"), [6.0, 6.0, 6.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_energy_overage"), [0.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(0.0)


def test_over_target_telemetry_prices_only_new_overage() -> None:
    """With an overage price, only delivery beyond the telemetry overshoot is priced."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[0.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        initial_energy=6.0,
        overage_price=0.05,
        supply_price=[-0.2, -0.2],
        max_supply_power=[1.0, 1.0],
    )

    cost = network.optimize()

    assert _outputs(load, "deferrable_load_energy_delivered")[-1] == pytest.approx(8.0)
    assert _outputs(load, "deferrable_load_energy_overage")[-1] == pytest.approx(2.0)
    assert cost == pytest.approx(-2.0 * 0.2 + 2.0 * 0.05)


def test_window_changes_update_reactively() -> None:
    """Moving a window only changes parameters and re-optimizes correctly."""
    network, load = _build_network(
        in_window=[1.0, 0.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 2.0, 0.0],
        supply_price=[0.1, 0.3],
    )
    assert network.optimize() == pytest.approx(2.0 * 0.1)

    load["in_window"] = np.array([0.0, 1.0])
    load["window_start"] = np.array([0.0, 1.0, 0.0])
    load["requirement"] = np.array([0.0, 0.0, 2.0])

    assert network.optimize() == pytest.approx(2.0 * 0.3)
    np.testing.assert_allclose(_outputs(load, "deferrable_load_power"), [0.0, 2.0], atol=1e-9)


def test_outputs_present() -> None:
    """The element exposes power, delivered, shortfall, overage and shadow price outputs."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 5.0],
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
    assert "deferrable_load_cap" in outputs


@pytest.mark.parametrize(
    ("deficit_price", "overage_price", "param"),
    [
        pytest.param(np.array([10.0, 10.0, -1.0]), None, "deficit_price", id="deficit"),
        pytest.param(10.0, -1.0, "overage_price", id="overage"),
    ],
)
def test_negative_price_is_rejected(deficit_price: np.ndarray | float, overage_price: float | None, param: str) -> None:
    """A negative price would book slack that is never missed or absorbed, so it is rejected."""
    network, _load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        deficit_price=deficit_price,
        overage_price=overage_price,
    )

    with pytest.raises(ValueError, match=f"{param} must be non-negative"):
        network.optimize()


@pytest.mark.parametrize(
    ("param", "value"),
    [
        pytest.param("deficit_price", np.array([10.0, -1.0, 10.0]), id="deficit"),
        pytest.param("overage_price", np.array([1.0, 1.0, -1.0]), id="overage"),
    ],
)
def test_negative_price_update_is_rejected(param: str, value: np.ndarray) -> None:
    """Updating a price to a negative value is rejected on the next optimization."""
    network, load = _build_network(
        in_window=[1.0, 1.0],
        window_start=[1.0, 0.0, 0.0],
        requirement=[0.0, 0.0, 4.0],
        overage_price=0.0,
    )
    network.optimize()

    load[param] = value

    with pytest.raises(ValueError, match=f"{param} must be non-negative"):
        network.optimize()
