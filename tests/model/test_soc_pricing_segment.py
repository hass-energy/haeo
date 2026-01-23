"""Tests for SOC pricing segment."""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements.segments.soc_pricing import SocPricingSegment


class MockBattery(Element[str]):
    """Minimal battery element for SOC pricing tests."""

    stored_energy: HighspyArray

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        stored_energy: HighspyArray,
    ) -> None:
        """Initialize the mock battery."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())
        self.stored_energy = stored_energy


class DummyElement(Element[str]):
    """Minimal non-battery element for segment endpoints."""

    def __init__(self, name: str, periods: NDArray[np.floating[Any]], solver: Highs) -> None:
        """Initialize the dummy element."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


def _create_solver() -> Highs:
    solver = Highs()
    solver.setOptionValue("output_flag", False)
    solver.setOptionValue("log_to_console", False)
    return solver


def test_soc_pricing_costs_apply_to_thresholds() -> None:
    """SOC pricing applies costs when stored energy violates thresholds."""
    solver = _create_solver()
    periods = np.array([1.0, 1.0])

    stored_energy = solver.addVariables(len(periods) + 1, lb=0, name_prefix="battery_e_", out_array=True)
    solver.addConstr(stored_energy[0] == 5.0)
    solver.addConstr(stored_energy[1] == 2.0)
    solver.addConstr(stored_energy[2] == 9.0)

    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)

    segment = SocPricingSegment(
        "soc",
        len(periods),
        periods,
        solver,
        spec={
            "segment_type": "soc_pricing",
            "undercharge_threshold": np.array([3.0, 3.0]),
            "overcharge_threshold": np.array([8.0, 8.0]),
            "undercharge_price": np.array([0.5, 0.5]),
            "overcharge_price": np.array([0.2, 0.2]),
        },
        source_element=battery,
        target_element=target,
    )

    segment.constraints()
    cost = segment.cost()
    assert cost is not None
    solver.minimize(cost)
    solver.run()

    assert segment.undercharge_slack is not None
    assert segment.overcharge_slack is not None
    undercharge_vals = solver.vals(segment.undercharge_slack)
    overcharge_vals = solver.vals(segment.overcharge_slack)

    assert tuple(float(value) for value in undercharge_vals) == (1.0, 0.0)
    assert tuple(float(value) for value in overcharge_vals) == (0.0, 1.0)
    assert float(solver.getObjectiveValue()) == 0.7
