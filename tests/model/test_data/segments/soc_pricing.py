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


def _battery_endpoints_fixed(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.addVariables(len(periods) + 1, lb=0, name_prefix="battery_e_", out_array=True)
    solver.addConstr(stored_energy[0] == 5.0)
    solver.addConstr(stored_energy[1] == 2.0)
    solver.addConstr(stored_energy[2] == 9.0)
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


def _battery_endpoints_free(solver: Highs, periods: NDArray[np.floating[Any]]) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.addVariables(len(periods) + 1, lb=0, name_prefix="battery_e_", out_array=True)
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


SCENARIOS: list[SegmentScenario] = [
    {
        "description": "SOC pricing applies costs outside thresholds",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0]),
            "discharge_price": np.array([0.5, 0.5]),
            "charge_price": np.array([0.2, 0.2]),
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
        "description": "SOC pricing supports discharge-only penalty",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0]),
            "discharge_price": np.array([0.5, 0.5]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {"below_slack": (1.0, 0.0), "objective_value": 0.5},
        "endpoint_factory": _battery_endpoints_fixed,
    },
    {
        "description": "SOC pricing supports charge-only penalty",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "threshold": np.array([3.0, 3.0]),
            "charge_price": np.array([0.2, 0.2]),
        },
        "periods": np.array([1.0, 1.0]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {"above_slack": (0.0, 6.0), "objective_value": 1.2},
        "endpoint_factory": _battery_endpoints_fixed,
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
        "description": "SOC pricing requires discharge threshold with price",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing", "discharge_price": np.array([0.1])},
        "periods": np.array([1.0]),
        "error": ValueError,
        "match": "threshold is required when discharge_price is set",
        "endpoint_factory": _battery_endpoints_free,
    },
    {
        "description": "SOC pricing requires charge threshold with price",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing", "charge_price": np.array([0.1])},
        "periods": np.array([1.0]),
        "error": ValueError,
        "match": "threshold is required when charge_price is set",
        "endpoint_factory": _battery_endpoints_free,
    },
]


__all__ = ["ERROR_SCENARIOS", "SCENARIOS"]
