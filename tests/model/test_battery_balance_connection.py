"""Tests for battery balance segment constraints.

This test suite verifies the battery balance connection's constraint formulation
using simplified mock batteries with controlled stored_energy values and SOC
constraints. The tests confirm that:

1. Downward flow: power_down = min(demand, available)
   - When demand <= available: power_down = demand (limited by lower's capacity)
   - When demand > available: power_down = available (limited by upper's energy)

2. Upward flow: power_up = max(0, excess)
   - When capacity stable: power_up = 0
   - When capacity shrinks: power_up = excess amount

The battery balance segment only provides one-sided bounds; the external SOC
constraints (E >= 0, E <= C) fully bind the solution to exact values.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Self

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.model.element import Element
from custom_components.haeo.model.elements.connection import CONNECTION_SEGMENTS, Connection
from custom_components.haeo.model.elements.segments.battery_balance import (
    BALANCE_ABSORBED_EXCESS,
    BALANCE_POWER_DOWN,
    BALANCE_POWER_UP,
    BALANCE_UNMET_DEMAND,
)


@dataclass
class MockBattery(Element[str]):
    """Simplified battery for testing balance connection constraints.

    Provides stored_energy as HiGHS linear expressions and adds basic SOC
    constraints (0 <= E <= capacity) to the solver.
    """

    name: str
    periods: NDArray[np.floating[Any]]
    capacity: tuple[float, ...]
    initial_charge: float
    _solver: Highs
    stored_energy: HighspyArray
    _energy_in: HighspyArray
    _energy_out: HighspyArray

    def __post_init__(self) -> None:
        """Initialize base element fields after dataclass setup."""
        super().__init__(name=self.name, periods=self.periods, solver=self._solver, output_names=frozenset())

    @classmethod
    def create(
        cls,
        name: str,
        periods: NDArray[np.floating[Any]],
        capacity: float | tuple[float, ...],
        initial_charge: float,
        solver: Highs,
    ) -> Self:
        """Create a mock battery with SOC constraints."""
        n_periods = len(periods)
        # Broadcast capacity to T+1 boundaries
        cap = tuple([float(capacity)] * (n_periods + 1)) if isinstance(capacity, float | int) else capacity

        # Create cumulative energy variables (T+1 values)
        energy_in = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_e_in_", out_array=True)
        energy_out = solver.addVariables(n_periods + 1, lb=0.0, name_prefix=f"{name}_e_out_", out_array=True)

        # Initial conditions
        solver.addConstr(energy_in[0] == initial_charge)
        solver.addConstr(energy_out[0] == 0.0)

        # Energy can only increase (cumulative)
        solver.addConstrs(energy_in[1:] >= energy_in[:-1])
        solver.addConstrs(energy_out[1:] >= energy_out[:-1])

        # Stored energy = cumulative in - cumulative out
        stored_energy = energy_in - energy_out

        # SOC constraints: 0 <= stored <= capacity
        for t in range(n_periods + 1):
            solver.addConstr(stored_energy[t] >= 0)
            solver.addConstr(stored_energy[t] <= cap[t])

        return cls(
            name=name,
            periods=periods,
            capacity=cap,
            initial_charge=initial_charge,
            _solver=solver,
            stored_energy=stored_energy,
            _energy_in=energy_in,
            _energy_out=energy_out,
        )

    def build_power_balance(self, periods: NDArray[np.floating[Any]]) -> None:
        """Build power balance constraint linking connections to energy change."""
        periods_array = periods
        # HiGHS expressions need multiplication by reciprocal, not division
        power_charge = (self._energy_in[1:] - self._energy_in[:-1]) * (1.0 / periods_array)
        power_discharge = (self._energy_out[1:] - self._energy_out[:-1]) * (1.0 / periods_array)
        net_battery_power = power_charge - power_discharge

        connection_power = self.connection_power()
        self._solver.addConstrs(connection_power == net_battery_power)


@dataclass
class BalanceTestScenario:
    """Test scenario for battery balance connection."""

    description: str
    n_periods: int
    periods: NDArray[np.floating[Any]]
    # Upper battery config
    upper_capacity: float | tuple[float, ...]
    upper_initial: float
    # Lower battery config (capacity can change over time for upward flow tests)
    lower_capacity: float | tuple[float, ...]
    lower_initial: float
    # Expected results
    expected_power_down: tuple[float, ...]
    expected_power_up: tuple[float, ...]


BALANCE_TEST_SCENARIOS: list[BalanceTestScenario] = [
    # Downward flow: demand <= available (limited by lower's space)
    BalanceTestScenario(
        description="Downward: lower has space, upper has more than enough",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=8.0,  # 8 kWh available
        lower_capacity=10.0,
        lower_initial=7.0,  # 3 kWh space (demand = 10 - 7 = 3)
        expected_power_down=(3.0,),  # min(3, 8) = 3
        expected_power_up=(0.0,),
    ),
    # Downward flow: demand > available (limited by upper's energy)
    BalanceTestScenario(
        description="Downward: lower has more space than upper has energy",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=2.0,  # Only 2 kWh available
        lower_capacity=10.0,
        lower_initial=3.0,  # 7 kWh space (demand = 10 - 3 = 7)
        expected_power_down=(2.0,),  # min(7, 2) = 2
        expected_power_up=(0.0,),
    ),
    # Downward flow: lower is full
    BalanceTestScenario(
        description="Downward: lower section full, no transfer needed",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=5.0,
        lower_capacity=10.0,
        lower_initial=10.0,  # Full - no space
        expected_power_down=(0.0,),  # min(0, 5) = 0
        expected_power_up=(0.0,),
    ),
    # Downward flow: upper is empty
    BalanceTestScenario(
        description="Downward: upper section empty, nothing to transfer",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=0.0,  # Empty
        lower_capacity=10.0,
        lower_initial=5.0,  # 5 kWh space
        expected_power_down=(0.0,),  # min(5, 0) = 0
        expected_power_up=(0.0,),
    ),
    # Upward flow: capacity shrinks
    BalanceTestScenario(
        description="Upward: capacity shrinks, excess moves up",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=0.0,
        # Capacity shrinks from 10 to 7 kWh
        lower_capacity=(10.0, 7.0),
        lower_initial=9.0,  # 9 kWh stored, excess = 9 - 7 = 2
        # demand = 10 - 9 = 1, but available = 0 (upper empty)
        expected_power_down=(0.0,),  # min(1, 0) = 0
        expected_power_up=(2.0,),  # max(0, 9 - 7) = 2
    ),
    # Upward flow: no capacity change
    BalanceTestScenario(
        description="Upward: capacity stable, no upward flow",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=3.0,
        lower_capacity=10.0,  # Stable capacity
        lower_initial=8.0,
        expected_power_down=(2.0,),  # Fill remaining space: 10 - 8 = 2
        expected_power_up=(0.0,),  # No excess
    ),
    # Multi-period scenario
    BalanceTestScenario(
        description="Multi-period: varying conditions",
        n_periods=3,
        periods=np.array([1.0, 1.0, 1.0]),
        upper_capacity=10.0,
        upper_initial=6.0,
        # Lower capacity shrinks from 10->8 between period 1 and 2
        lower_capacity=(10.0, 10.0, 8.0, 8.0),
        lower_initial=5.0,
        # Period 0: demand=5, available=6 -> power_down=5
        #   lower: 5+5=10, upper: 6-5=1
        # Period 1: demand=0, available=1, excess=10-8=2 -> power_up=2
        #   lower: 10-2=8, upper: 1+2=3
        # Period 2: demand=0, available=3, excess=0 -> no transfer
        expected_power_down=(5.0, 0.0, 0.0),
        expected_power_up=(0.0, 2.0, 0.0),
    ),
    # Edge case: both sections empty
    BalanceTestScenario(
        description="Edge: both sections empty",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=0.0,
        lower_capacity=10.0,
        lower_initial=0.0,
        expected_power_down=(0.0,),  # min(10, 0) = 0
        expected_power_up=(0.0,),
    ),
    # Edge case: both sections full
    BalanceTestScenario(
        description="Edge: both sections full",
        n_periods=1,
        periods=np.array([1.0]),
        upper_capacity=10.0,
        upper_initial=10.0,
        lower_capacity=10.0,
        lower_initial=10.0,
        expected_power_down=(0.0,),  # min(0, 10) = 0
        expected_power_up=(0.0,),
    ),
]


@pytest.mark.parametrize(
    "scenario",
    BALANCE_TEST_SCENARIOS,
    ids=lambda s: s.description.lower().replace(" ", "_").replace(",", "").replace(":", ""),
)
def test_battery_balance_connection(scenario: BalanceTestScenario, solver: Highs) -> None:
    """Verify balance connection produces correct power flows."""
    # Create mock batteries
    upper = MockBattery.create(
        name="upper",
        periods=scenario.periods,
        capacity=scenario.upper_capacity,
        initial_charge=scenario.upper_initial,
        solver=solver,
    )
    lower = MockBattery.create(
        name="lower",
        periods=scenario.periods,
        capacity=scenario.lower_capacity,
        initial_charge=scenario.lower_initial,
        solver=solver,
    )

    # Create balance connection
    connection = Connection(
        name="balance",
        periods=scenario.periods,
        solver=solver,
        source="upper",
        target="lower",
        segments={"balance": {"segment_type": "battery_balance"}},
    )
    connection.set_endpoints(upper, lower)
    upper.register_connection(connection, "source")
    lower.register_connection(connection, "target")

    # Build power balance for batteries (links connections to energy change)
    upper.build_power_balance(scenario.periods)
    lower.build_power_balance(scenario.periods)

    # Apply balance connection constraints
    connection.constraints()

    # Collect cost from element (aggregates all @cost methods)
    connection_cost = connection.cost()
    if connection_cost is not None:
        solver.minimize(connection_cost)

    # Solve
    solver.run()

    # Extract results
    outputs = connection.outputs()
    segments_output = outputs[CONNECTION_SEGMENTS]
    assert isinstance(segments_output, Mapping)
    segment_outputs = segments_output["balance"]
    assert isinstance(segment_outputs, Mapping)
    power_down = segment_outputs[BALANCE_POWER_DOWN].values
    power_up = segment_outputs[BALANCE_POWER_UP].values

    # Verify power flows match expectations
    assert power_down == pytest.approx(scenario.expected_power_down, abs=1e-6), (
        f"power_down mismatch: got {power_down}, expected {scenario.expected_power_down}"
    )
    assert power_up == pytest.approx(scenario.expected_power_up, abs=1e-6), (
        f"power_up mismatch: got {power_up}, expected {scenario.expected_power_up}"
    )


def test_battery_balance_connection_outputs_structure(solver: Highs) -> None:
    """Verify outputs method returns expected structure before optimization."""
    periods = np.array([1.0, 1.0])
    upper = MockBattery.create("upper", periods, 10.0, 5.0, solver)
    lower = MockBattery.create("lower", periods, 10.0, 3.0, solver)

    connection = Connection(
        name="balance",
        periods=periods,
        solver=solver,
        source="upper",
        target="lower",
        segments={"balance": {"segment_type": "battery_balance"}},
    )
    connection.set_endpoints(upper, lower)
    connection.constraints()

    # Run solver
    solver.run()

    outputs = connection.outputs()
    segments_output = outputs[CONNECTION_SEGMENTS]
    assert isinstance(segments_output, Mapping)
    segment_outputs = segments_output["balance"]
    assert isinstance(segment_outputs, Mapping)

    # Check required outputs exist
    assert BALANCE_POWER_DOWN in segment_outputs
    assert BALANCE_POWER_UP in segment_outputs
    assert BALANCE_UNMET_DEMAND in segment_outputs
    assert BALANCE_ABSORBED_EXCESS in segment_outputs

    # Check constraint shadow prices exist
    assert "balance_down_lower_bound" in segment_outputs
    assert "balance_down_slack_bound" in segment_outputs
    assert "balance_up_upper_bound" in segment_outputs
    assert "balance_up_slack_bound" in segment_outputs

    # Verify output metadata
    assert segment_outputs[BALANCE_POWER_DOWN].unit == "kW"
    assert segment_outputs[BALANCE_POWER_UP].unit == "kW"
    assert segment_outputs[BALANCE_POWER_DOWN].direction == "+"
    assert segment_outputs[BALANCE_POWER_UP].direction == "-"
