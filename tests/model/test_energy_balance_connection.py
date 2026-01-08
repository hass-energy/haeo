"""Tests for EnergyBalanceConnection constraints.

This test suite verifies the energy balance connection's constraint formulation
using simplified mock partitions with controlled stored_energy values and SOC
constraints. The tests confirm that:

1. Downward flow: power_down = min(demand, available)
   - When demand <= available: power_down = demand (limited by lower's capacity)
   - When demand > available: power_down = available (limited by upper's energy)

2. Upward flow: power_up = max(0, excess)
   - When capacity stable: power_up = 0
   - When capacity shrinks: power_up = excess amount

The energy balance connection only provides one-sided bounds; the external SOC
constraints (E >= 0, E <= C) fully bind the solution to exact values.
"""

from dataclasses import dataclass
from typing import Self

from highspy import Highs
from highspy.highs import HighspyArray
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.model.elements.energy_balance_connection import EnergyBalanceConnection


@dataclass
class MockPartition:
    """Simplified partition for testing balance connection constraints.

    Provides stored_energy as HiGHS linear expressions and adds basic SOC
    constraints (0 <= E <= capacity) to the solver.
    """

    name: str
    n_periods: int
    capacity: tuple[float, ...]
    initial_charge: float
    _solver: Highs
    stored_energy: HighspyArray
    _energy_in: HighspyArray
    _energy_out: HighspyArray
    _connections: list[tuple[EnergyBalanceConnection, str]]

    @classmethod
    def create(
        cls,
        name: str,
        n_periods: int,
        capacity: float | tuple[float, ...],
        initial_charge: float,
        solver: Highs,
    ) -> Self:
        """Create a mock partition with SOC constraints."""
        # Broadcast capacity to T+1 fence posts
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
            n_periods=n_periods,
            capacity=cap,
            initial_charge=initial_charge,
            _solver=solver,
            stored_energy=stored_energy,
            _energy_in=energy_in,
            _energy_out=energy_out,
            _connections=[],
        )

    def register_connection(self, connection: EnergyBalanceConnection, end: str) -> None:
        """Register a connection to this partition."""
        self._connections.append((connection, end))

    def connection_power(self, _periods: NDArray[np.floating]) -> HighspyArray:
        """Calculate net power from all registered connections."""
        n = self.n_periods
        # Start with zero power
        net_power: HighspyArray | float = 0.0

        for conn, end in self._connections:
            # Power flowing into this battery from the connection
            power = conn.power_into_source if end == "source" else conn.power_into_target
            net_power = net_power + power

        # If still a scalar, create array
        if isinstance(net_power, float | int):
            return self._solver.addVariables(n, lb=0.0, ub=0.0, name_prefix="zero_power_", out_array=True)
        return net_power

    def build_power_balance(self, periods: tuple[float, ...]) -> None:
        """Build power balance constraint linking connections to energy change."""
        periods_array = np.array(periods)
        # HiGHS expressions need multiplication by reciprocal, not division
        power_charge = (self._energy_in[1:] - self._energy_in[:-1]) * (1.0 / periods_array)
        power_discharge = (self._energy_out[1:] - self._energy_out[:-1]) * (1.0 / periods_array)
        net_battery_power = power_charge - power_discharge

        connection_power = self.connection_power(periods_array)
        self._solver.addConstrs(connection_power == net_battery_power)


@dataclass
class BalanceTestScenario:
    """Test scenario for energy balance connection."""

    description: str
    n_periods: int
    periods: tuple[float, ...]
    # Upper partition config
    upper_capacity: float | tuple[float, ...]
    upper_initial: float
    # Lower partition config (capacity can change over time for upward flow tests)
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
        periods=(1.0,),
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
        periods=(1.0,),
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
        periods=(1.0,),
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
        periods=(1.0,),
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
        periods=(1.0,),
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
        periods=(1.0,),
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
        periods=(1.0, 1.0, 1.0),
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
        periods=(1.0,),
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
        periods=(1.0,),
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
def test_energy_balance_connection(scenario: BalanceTestScenario, solver: Highs) -> None:
    """Verify balance connection produces correct power flows."""
    # Create mock partitions
    upper = MockPartition.create(
        name="upper",
        n_periods=scenario.n_periods,
        capacity=scenario.upper_capacity,
        initial_charge=scenario.upper_initial,
        solver=solver,
    )
    lower = MockPartition.create(
        name="lower",
        n_periods=scenario.n_periods,
        capacity=scenario.lower_capacity,
        initial_charge=scenario.lower_initial,
        solver=solver,
    )

    # Create balance connection
    connection = EnergyBalanceConnection(
        name="balance",
        periods=scenario.periods,
        solver=solver,
        upper="upper",
        lower="lower",
        capacity_lower=scenario.lower_capacity,
    )

    # Set partition references and build constraints
    # MockPartition provides the same interface as EnergyStorage but isn't a subtype
    connection.set_partition_references(upper, lower)  # type: ignore[arg-type]

    # Build power balance for partitions (links connections to energy change)
    upper.build_power_balance(scenario.periods)
    lower.build_power_balance(scenario.periods)

    # Build balance connection constraints (triggers reactive constraint building)
    connection.constraints()

    # Add cost to objective (required for min/max constraint behavior via slack penalties)
    cost_expr = connection.cost()
    if cost_expr is not None:
        solver.minimize(cost_expr)

    # Solve
    solver.run()

    # Extract results
    outputs = connection.outputs()
    power_down = outputs["balance_power_down"].values
    power_up = outputs["balance_power_up"].values

    # Verify power flows match expectations
    assert power_down == pytest.approx(scenario.expected_power_down, abs=1e-6), (
        f"power_down mismatch: got {power_down}, expected {scenario.expected_power_down}"
    )
    assert power_up == pytest.approx(scenario.expected_power_up, abs=1e-6), (
        f"power_up mismatch: got {power_up}, expected {scenario.expected_power_up}"
    )


def test_energy_balance_connection_missing_references(solver: Highs) -> None:
    """Verify error when partition references not set."""
    connection = EnergyBalanceConnection(
        name="balance",
        periods=(1.0,),
        solver=solver,
        upper="upper",
        lower="lower",
        capacity_lower=10.0,
    )

    with pytest.raises(ValueError, match="Partition references not set"):
        connection.constraints()


def test_energy_balance_connection_outputs_structure(solver: Highs) -> None:
    """Verify outputs method returns expected structure before optimization."""
    upper = MockPartition.create("upper", 2, 10.0, 5.0, solver)
    lower = MockPartition.create("lower", 2, 10.0, 3.0, solver)

    connection = EnergyBalanceConnection(
        name="balance",
        periods=(1.0, 1.0),
        solver=solver,
        upper="upper",
        lower="lower",
        capacity_lower=10.0,
    )
    # MockPartition provides the same interface as EnergyStorage but isn't a subtype
    connection.set_partition_references(upper, lower)  # type: ignore[arg-type]
    connection.constraints()

    # Run solver
    solver.run()

    outputs = connection.outputs()

    # Check required outputs exist
    assert "balance_power_down" in outputs
    assert "balance_power_up" in outputs
    assert "balance_unmet_demand" in outputs
    assert "balance_absorbed_excess" in outputs

    # Check constraint shadow prices exist
    assert "balance_down_lower_bound" in outputs
    assert "balance_down_slack_bound" in outputs
    assert "balance_up_upper_bound" in outputs
    assert "balance_up_slack_bound" in outputs

    # Verify output metadata
    assert outputs["balance_power_down"].unit == "kW"
    assert outputs["balance_power_up"].unit == "kW"
    assert outputs["balance_power_down"].direction == "+"
    assert outputs["balance_power_up"].direction == "-"
