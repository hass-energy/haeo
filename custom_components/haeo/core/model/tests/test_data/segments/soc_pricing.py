"""SOC pricing segment scenarios."""

from typing import Any

import numpy as np
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.segments import SocPricingSegment
from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util.solver_rows import add_rows
from numpy.typing import NDArray

from ..segment_types import SegmentErrorScenario, SegmentScenario


class MockBattery(Element[str]):
    """Minimal battery element for SOC pricing scenarios."""

    stored_energy: LinearArray

    def __init__(
        self,
        name: str,
        periods: NDArray[np.float64],
        solver: Solver,
        stored_energy: LinearArray,
    ) -> None:
        """Initialize the mock battery."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())
        self.stored_energy = stored_energy


class DummyElement(Element[str]):
    """Minimal non-battery element for segment endpoints."""

    def __init__(self, name: str, periods: NDArray[np.float64], solver: Solver) -> None:
        """Initialize the dummy element."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


def _battery_endpoints_fixed(solver: Solver, periods: NDArray[np.float64]) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.add_variables(len(periods) + 1, name="stored_energy")
    add_rows(solver, stored_energy[0] == 5.0)
    add_rows(solver, stored_energy[1] == 2.0)
    add_rows(solver, stored_energy[2] == 9.0)
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


def _battery_endpoints_free(solver: Solver, periods: NDArray[np.float64]) -> tuple[Element[Any], Element[Any]]:
    stored_energy = solver.add_variables(len(periods) + 1, name="stored_energy")
    battery = MockBattery("battery", periods, solver, stored_energy)
    target = DummyElement("target", periods, solver)
    return battery, target


SCENARIOS: list[SegmentScenario] = [
    {
        "description": "SOC pricing applies costs outside thresholds",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "discharge_energy_threshold": np.array([3.0, 3.0]),
            "charge_capacity_threshold": np.array([8.0, 8.0]),
            "discharge_energy_price": np.array([0.5, 0.5]),
            "charge_capacity_price": np.array([0.2, 0.2]),
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {
            "discharge_energy_slack": (1.0, 0.0),
            "charge_capacity_slack": (0.0, 1.0),
            "objective_value": 0.6,
        },
        "endpoint_factory": _battery_endpoints_fixed,
    },
    {
        "description": "SOC pricing supports discharge-only penalty",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "discharge_energy_threshold": np.array([3.0, 3.0]),
            "discharge_energy_price": np.array([0.5, 0.5]),
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {"discharge_energy_slack": (1.0, 0.0), "objective_value": 0.5},
        "endpoint_factory": _battery_endpoints_fixed,
    },
    {
        "description": "SOC pricing supports charge-only penalty",
        "factory": SocPricingSegment,
        "spec": {
            "segment_type": "soc_pricing",
            "charge_capacity_threshold": np.array([8.0, 8.0]),
            "charge_capacity_price": np.array([0.2, 0.2]),
        },
        "periods": np.array([1.0, 0.5]),
        "inputs": {"minimize_cost": True},
        "expected_outputs": {"charge_capacity_slack": (0.0, 1.0), "objective_value": 0.1},
        "endpoint_factory": _battery_endpoints_fixed,
    },
    {
        "description": "SOC pricing passes through power",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing"},
        "periods": np.array([1.0, 0.5]),
        "inputs": {"power_in": (3.0, 4.0)},
        "expected_outputs": {
            "power_in": (3.0, 4.0),
            "power_out": (3.0, 4.0),
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
        "spec": {"segment_type": "soc_pricing", "discharge_energy_price": np.array([0.1])},
        "periods": np.array([1.0]),
        "error": ValueError,
        "match": "discharge_energy_threshold is required when discharge_energy_price is set",
        "endpoint_factory": _battery_endpoints_free,
    },
    {
        "description": "SOC pricing requires charge threshold with price",
        "factory": SocPricingSegment,
        "spec": {"segment_type": "soc_pricing", "charge_capacity_price": np.array([0.1])},
        "periods": np.array([1.0]),
        "error": ValueError,
        "match": "charge_capacity_threshold is required when charge_capacity_price is set",
        "endpoint_factory": _battery_endpoints_free,
    },
]


__all__ = ["ERROR_SCENARIOS", "SCENARIOS"]
