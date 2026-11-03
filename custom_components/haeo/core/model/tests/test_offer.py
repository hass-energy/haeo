"""Tests for offer curves."""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.infeasibility import Relaxation, RowLabel
from custom_components.haeo.core.model.linear import LinearArray


def _home(*, initial_charge: float) -> tuple[Network, LinearArray]:
    """Return a solved home with a 2 kW load, a 5 kWh battery and a grid, and its net grid import.

    Over two one-hour periods import costs 0.30 then 0.50 $/kWh, and export pays 0.10 $/kWh.
    """
    network = Network(name="home", periods=np.array([1.0, 1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "house", "is_source": False, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 5.0, "initial_charge": initial_charge}
    )
    grid_import = network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "grid:import",
            "tags": {0},
            "source": "grid",
            "target": "house",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
                "pricing": {"segment_type": "pricing", "price": np.array([0.30, 0.50])},
            },
        }
    )
    grid_export = network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "grid:export",
            "tags": {0},
            "source": "house",
            "target": "grid",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
                "pricing": {"segment_type": "pricing", "price": np.array([-0.10, -0.10])},
            },
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "load:feed",
            "tags": {0},
            "source": "house",
            "target": "load",
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 2.0, "fixed": True}},
        }
    )
    for name, source, target in (("battery:charge", "house", "battery"), ("battery:discharge", "battery", "house")):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": name,
                "tags": {0},
                "source": source,
                "target": target,
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
            }
        )
    network.optimize()
    return network, grid_import.total_power_in - grid_export.total_power_in


def _curve(network: Network, flow: LinearArray, period: int) -> list[tuple[float, float]]:
    (curve,) = network.offer_curves(flow, windows=[[period]], low=[-1.0], high=[1.0])
    assert curve.periods == (period,)
    return [(round(step.price, 6), round(step.power, 6)) for step in curve.steps]


def test_offer_curve_steps_where_stored_energy_changes_use() -> None:
    """Each step is a price at which the battery's next kWh is worth more somewhere else.

    The battery's first 2 kWh replace the second period's 0.50 import, and more
    is only worth the 0.10 export. Below an import price of 0.10 the battery
    fills, up to 0.50 it keeps 2 kWh for later, above 0.50 the first period's
    load runs from it, and above 0.50 export it all goes to the grid.
    """
    network, flow = _home(initial_charge=3.0)

    assert _curve(network, flow, 0) == [(-1.0, 4.0), (-0.2, 1.0), (0.2, 0.0), (0.4, -1.0)]


def test_offer_curve_of_a_later_period() -> None:
    """A later period's curve shifts that period's prices only."""
    network, flow = _home(initial_charge=0.0)

    # Below an import price of zero the battery is filled to be paid for it, below 0.30 the load
    # imports, above 0.30 the load runs from the battery charged in the first period, and above an
    # export price of 0.30 the battery is filled in the first period to export what the load leaves
    assert _curve(network, flow, 1) == [(-1.0, 7.0), (-0.5, 2.0), (-0.2, 0.0), (0.2, -3.0)]


def test_offer_curve_of_a_window_shifts_every_period_in_it() -> None:
    """A price that holds over the whole window can only move energy out of it, not between its periods.

    With both periods' prices shifted together the battery's charge is only
    worth keeping past the window when import is paid for, so the window's
    average power moves far less than the first period's does on its own.
    """
    network, flow = _home(initial_charge=3.0)

    (curve,) = network.offer_curves(flow, windows=[[0, 1]], low=[-1.0], high=[1.0])

    assert curve.periods == (0, 1)
    assert [(round(step.price, 6), round(step.power, 6)) for step in curve.steps] == [
        (-1.0, 3.0),
        (-0.5, 2.0),
        (-0.3, 0.5),
    ]


def test_offer_curve_measures_the_whole_plan_at_each_step() -> None:
    """A measured quantity is read from the whole plan, so it sees where the battery makes up for a step.

    Weighting each period's grid energy by 1.0 then 0.5, exporting the battery's
    last kWh in the first period costs the second period 2 kWh of import.
    """
    network, flow = _home(initial_charge=3.0)
    measure = (flow * np.array([1.0, 0.5])).total()

    (curve,) = network.offer_curves(flow, windows=[[0]], low=[-1.0], high=[1.0], measure=measure)

    assert [round(step.measure, 6) for step in curve.steps] == [2.5, 1.0, 0.5, 0.0]


def test_offer_curve_leaves_the_plan_unchanged() -> None:
    """Tracing curves runs on a copy, so the plan and its warm start are untouched."""
    network, flow = _home(initial_charge=3.0)
    plan = np.asarray(network._solver.getSolution().col_value)

    network.offer_curves(flow, windows=[[0], [1], [0, 1]], low=[-1.0] * 3, high=[1.0] * 3)

    np.testing.assert_array_equal(network._solver.getSolution().col_value, plan)


def test_offer_curve_step_at_takes_the_step_above_on_an_edge() -> None:
    """A price on a step's edge reads the step that starts there."""
    network, flow = _home(initial_charge=3.0)
    (curve,) = network.offer_curves(flow, windows=[[0]], low=[-1.0], high=[1.0])

    assert curve.step_at(-1.0).power == pytest.approx(4.0)
    assert curve.step_at(0.0).power == pytest.approx(1.0)
    assert curve.step_at(curve.steps[2].price).power == pytest.approx(0.0)
    assert curve.steps[-1].price == pytest.approx(0.4)


def test_offer_curve_refused_for_a_relaxed_plan() -> None:
    """A relaxed plan's model has its bounds back, so it has no curve to trace."""
    network, flow = _home(initial_charge=3.0)
    network.relaxations = (Relaxation(RowLabel("battery", "soc", 0), 1.0),)

    with pytest.raises(ValueError, match="relaxing constraints"):
        network.offer_curves(flow, windows=[[0]], low=[-1.0], high=[1.0])
