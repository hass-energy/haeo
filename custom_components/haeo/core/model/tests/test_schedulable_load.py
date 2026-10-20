"""Tests for the schedulable load model element."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
    IntegerMode,
    SchedulableLoad,
    SchedulableLoadOutputName,
    SegmentSpec,
)


def _build_network(
    *,
    supply_price: list[float],
    profile_power: list[float],
    profile_duration: list[float],
    in_window: list[float] | None = None,
    window_start: list[float] | None = None,
    periods: list[float] | None = None,
    deficit_price: float = 10.0,
    elapsed: float | None = None,
    window_started: bool = False,
    integer_mode: IntegerMode = "none",
    max_supply_power: float | None = None,
) -> tuple[Network, SchedulableLoad]:
    """Build a grid-fed schedulable load network, one-hour periods by default."""
    n = len(supply_price)
    network = Network(name="test_network", periods=np.array(periods if periods is not None else [1.0] * n))

    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    load = network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
            "name": "load",
            "profile_power": np.array(profile_power),
            "profile_duration": np.array(profile_duration),
            "in_window": np.array(in_window if in_window is not None else [1.0] * n),
            "window_start": np.array(window_start if window_start is not None else [0.0] * (n + 1)),
            "deficit_price": deficit_price,
            "elapsed": elapsed,
            "window_started": window_started,
            "integer_mode": integer_mode,
            "is_source": False,
            "is_sink": True,
        }
    )
    segments: dict[str, SegmentSpec] = {
        "pricing": {"segment_type": "pricing", "price": np.array(supply_price)},
    }
    if max_supply_power is not None:
        segments["power_limit"] = {"segment_type": "power_limit", "max_power": np.full(n, max_supply_power)}
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


def _outputs(load: SchedulableLoad, name: SchedulableLoadOutputName) -> np.ndarray:
    return np.array(load.outputs()[name].values)


def test_run_starts_at_cheapest_boundary() -> None:
    """The run starts where its whole duration is cheapest."""
    network, load = _build_network(
        supply_price=[0.3, 0.2, 0.1, 0.25],
        profile_power=[2.0],
        profile_duration=[2.0],
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 2.0, 2.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "schedulable_load_start"), [0.0, 1.0, 0.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(2.0 * 0.2 + 2.0 * 0.1)


def test_profile_steps_follow_the_start() -> None:
    """Each profile step lands in the period it overlaps after the start."""
    network, load = _build_network(
        supply_price=[0.3, 0.1, 0.2],
        profile_power=[3.0, 1.0],
        profile_duration=[1.0, 1.0],
    )

    network.optimize()

    # Starting at boundary 1 puts the 3 kW step in the cheapest period.
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 3.0, 1.0], atol=1e-9)


def test_partial_period_overlap_spreads_energy() -> None:
    """A run ending inside a period consumes only the overlapping energy there."""
    network, load = _build_network(
        supply_price=[0.1, 0.1, 0.5],
        profile_power=[2.0],
        profile_duration=[1.5],
    )

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [2.0, 1.0, 0.0], atol=1e-9)


def test_variable_width_periods() -> None:
    """Start columns follow variable-width periods."""
    network, load = _build_network(
        supply_price=[0.5, 0.1, 0.1],
        periods=[0.5, 0.5, 2.0],
        profile_power=[2.0],
        profile_duration=[1.0],
    )

    network.optimize()

    # Starting at boundary 1 (0.5 h) runs 0.5 h in period 1 and 0.5 h in period 2.
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 2.0, 0.5], atol=1e-9)


def test_run_must_fit_inside_window() -> None:
    """A start whose run would pass the window end is not allowed."""
    network, load = _build_network(
        supply_price=[0.5, 0.4, 0.3, 0.1],
        profile_power=[1.0],
        profile_duration=[2.0],
        in_window=[1.0, 1.0, 1.0, 0.0],
    )

    network.optimize()

    # Boundary 2 would run into the cheap period outside the window.
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 1.0, 1.0, 0.0], atol=1e-9)


def test_each_window_gets_one_run() -> None:
    """Touching windows are separate and each receives its own run."""
    network, load = _build_network(
        supply_price=[0.1, 0.2, 0.3, 0.1],
        profile_power=[1.0],
        profile_duration=[1.0],
        window_start=[0.0, 0.0, 1.0, 0.0, 0.0],
    )

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [1.0, 0.0, 0.0, 1.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "schedulable_load_energy_missed"), [0.0] * 5, atol=1e-9)


def test_window_too_short_books_missed_run() -> None:
    """A window shorter than the profile books a missed run priced per kWh."""
    network, load = _build_network(
        supply_price=[0.1, 0.1, 0.1],
        profile_power=[2.0],
        profile_duration=[2.0],
        in_window=[1.0, 0.0, 0.0],
        deficit_price=5.0,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "schedulable_load_energy_missed"), [0.0, 4.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(5.0 * 4.0)


def test_run_in_progress_is_committed() -> None:
    """A run in progress finishes its profile from the horizon start."""
    network, load = _build_network(
        supply_price=[0.5, 0.5, 0.1, 0.1],
        profile_power=[2.0],
        profile_duration=[2.0],
        elapsed=0.5,
        window_started=True,
    )

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [2.0, 1.0, 0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "schedulable_load_start"), [0.0] * 5, atol=1e-9)


def test_no_start_while_committed_run_continues() -> None:
    """A later window cannot start a run before the committed run finishes."""
    network, load = _build_network(
        supply_price=[0.5, 0.1, 0.5, 0.5],
        profile_power=[1.0],
        profile_duration=[2.0],
        in_window=[0.0, 1.0, 1.0, 1.0],
        elapsed=0.5,
    )

    network.optimize()

    # The committed run lasts until 1.5 h, so the next run starts at boundary 2.
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [1.0, 0.5, 1.0, 1.0], atol=1e-9)


def test_window_already_started_needs_no_run() -> None:
    """A window whose run already happened neither runs again nor books a miss."""
    network, load = _build_network(
        supply_price=[0.1, 0.1],
        profile_power=[1.0],
        profile_duration=[1.0],
        window_started=True,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 0.0], atol=1e-9)
    np.testing.assert_allclose(_outputs(load, "schedulable_load_energy_missed"), [0.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("integer_mode", "expected_start", "expected_missed"),
    [
        pytest.param("none", [0.5, 0.5, 0.0], 0.0, id="none"),
        pytest.param("first", [0.0, 0.5, 0.5], 0.0, id="first"),
        pytest.param("all", [0.0, 0.0, 0.0], 1.0, id="all"),
    ],
)
def test_integer_mode_controls_fractional_starts(
    integer_mode: IntegerMode,
    expected_start: list[float],
    expected_missed: float,
) -> None:
    """A supply limit below the load power splits starts unless they are integer."""
    network, load = _build_network(
        supply_price=[0.1, 0.2, 0.3],
        profile_power=[2.0],
        profile_duration=[1.0],
        max_supply_power=1.0,
        integer_mode=integer_mode,
    )

    network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_start")[:-1], expected_start, atol=1e-6)
    assert _outputs(load, "schedulable_load_energy_missed")[-1] == pytest.approx(2.0 * expected_missed, abs=1e-6)


def test_integer_solve_keeps_shadow_prices() -> None:
    """An integer solve prices the energy its chosen run consumes like an integral linear solve.

    The starts are fixed for the dual solve, so periods the run does not
    reach have no marginal start to price them and report zero.
    """
    shadow_prices = {}
    for integer_mode in ("none", "all"):
        network, load = _build_network(
            supply_price=[0.3, 0.1, 0.2],
            profile_power=[1.0],
            profile_duration=[1.0],
            integer_mode=integer_mode,
        )
        network.optimize()
        shadow_prices[integer_mode] = _outputs(load, "schedulable_load_profile")

    assert shadow_prices["all"][1] > 0.0
    assert shadow_prices["all"][1] == pytest.approx(shadow_prices["none"][1])


def test_integer_starts_free_again_on_next_solve() -> None:
    """Integer starts fixed for shadow prices are released before the next solve."""
    network, load = _build_network(
        supply_price=[0.1, 0.3, 0.2],
        profile_power=[1.0],
        profile_duration=[1.0],
        integer_mode="first",
    )
    network.optimize()
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [1.0, 0.0, 0.0], atol=1e-9)

    load.window_started = True
    network.optimize()
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 0.0, 0.0], atol=1e-9)

    load.window_started = False
    network.optimize()
    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [1.0, 0.0, 0.0], atol=1e-9)


@pytest.mark.parametrize("integer_mode", ["none", "first", "all"])
def test_time_preference_never_outweighs_cost(integer_mode: IntegerMode) -> None:
    """The secondary objective's preference for earlier power never buys a dearer start."""
    network, load = _build_network(
        supply_price=[0.2, 0.199, 0.3, 0.3],
        profile_power=[1.0],
        profile_duration=[1.0],
        integer_mode=integer_mode,
    )

    cost = network.optimize()

    np.testing.assert_allclose(_outputs(load, "schedulable_load_power"), [0.0, 1.0, 0.0, 0.0], atol=1e-9)
    assert cost == pytest.approx(0.199)
