"""SOC pricing segment scenarios."""

from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements.segments import SocPricingSegment

from ..segment_types import SegmentErrorScenario, SegmentScenario


class MockBattery(Element[str]):
    """Minimal battery element for SOC pricing scenarios."""

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


def _battery_endpoints_with_values(
    solver: Highs,
    periods: NDArray[np.floating[Any]],
    stored_energy_values: list[float],
) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.addVariables(len(periods) + 1, lb=0, name_prefix="battery_e_", out_array=True)
    for index, value in enumerate(stored_energy_values):
        solver.addConstr(stored_energy[index] == float(value))
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


def _battery_endpoints_fixed(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    return _battery_endpoints_with_values(solver, periods, [5.0, 2.0, 9.0])


def _battery_endpoints_enter(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    return _battery_endpoints_with_values(solver, periods, [5.0, 4.0, 3.0, 2.0])


def _battery_endpoints_dwell(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    return _battery_endpoints_with_values(solver, periods, [5.0, 2.0, 2.0, 2.0])


def _battery_endpoints_above_cycle(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    return _battery_endpoints_with_values(solver, periods, [5.0, 4.0, 5.0, 4.0])


def _battery_endpoints_free(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.addVariables(len(periods) + 1, lb=0, name_prefix="battery_e_", out_array=True)
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


SCENARIOS: list[SegmentScenario] = [
    {
        "description": "SOC pricing applies inventory costs outside thresholds",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0]),
            "discharge_violation_price": np.array([0.5, 0.5]),
            "charge_violation_price": np.array([0.2, 0.2]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {
            "below_slack": (1.0, 0.0),
            "above_slack": (0.0, 6.0),
            "objective_value": 1.7,
        },
        "endpoint_factory": _battery_endpoints_fixed,
    },
    {
        "description": "SOC pricing movement costs only charge on entry not dwell",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0, 3.0]),
            "discharge_movement_price": np.array([0.5, 0.5, 0.5]),
        },
        "periods": np.array([1.0, 1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {
            "_below_slack": (1.0, 1.0, 1.0),
            "_below_enter": (1.0, 0.0, 0.0),
            "_below_recover": (0.0, 0.0, 0.0),
            "objective_value": 0.50003,
        },
        "endpoint_factory": _battery_endpoints_dwell,
    },
    {
        "description": "SOC pricing movement captures entering below threshold",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0, 3.0]),
            "discharge_movement_price": np.array([0.5, 0.5, 0.5]),
        },
        "periods": np.array([1.0, 1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {
            "_below_slack": (0.0, 0.0, 1.0),
            "_below_enter": (0.0, 0.0, 1.0),
            "_below_recover": (0.0, 0.0, 0.0),
            "objective_value": 0.50001,
        },
        "endpoint_factory": _battery_endpoints_enter,
    },
    {
        "description": "SOC pricing movement supports above-threshold enter and recover",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0, 3.0]),
            "charge_violation_price": np.array([0.2, 0.2, 0.2]),
            "charge_movement_price": np.array([0.3, 0.3, 0.3]),
            "discharge_movement_price": np.array([0.1, 0.1, 0.1]),
        },
        "periods": np.array([1.0, 1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {
            "_above_slack": (1.0, 2.0, 1.0),
            "_above_enter": (1.0, 1.0, 0.0),
            "_above_recover": (0.0, 0.0, 1.0),
            "objective_value": 1.50004,
        },
        "endpoint_factory": _battery_endpoints_above_cycle,
    },
    {
        "description": "SOC pricing passes through power",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing"},
        "periods": np.array([1.0, 1.0]),
        "inputs": {"power_in_st": (1.0, 2.0), "power_in_ts": (3.0, 4.0)},
        "expected_outputs": {
            "power_in_st": (1.0, 2.0),
            "power_out_st": (1.0, 2.0),
            "power_in_ts": (3.0, 4.0),
            "power_out_ts": (3.0, 4.0),
        },
        "endpoint_factory": _battery_endpoints_free,
    },
]


ERROR_SCENARIOS: list[SegmentErrorScenario] = [
    {
        "description": "SOC pricing requires a battery endpoint",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing"},
        "periods": np.array([1.0]),
        "error": TypeError,
        "match": "SOC pricing segment requires a battery element endpoint",
    },
    {
        "description": "SOC pricing requires threshold when configured",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing", "discharge_violation_price": np.array([0.1])},
        "periods": np.array([1.0]),
        "error": ValueError,
        "match": "threshold is required when SOC pricing is configured",
        "endpoint_factory": _battery_endpoints_free,
    },
]


__all__ = ["ERROR_SCENARIOS", "SCENARIOS"]
