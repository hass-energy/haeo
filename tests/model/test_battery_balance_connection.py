"""Model battery balance connection tests.

Tests for the BatteryBalanceConnection element which provides lossless energy
redistribution between adjacent battery sections, enforcing that lower sections
fill to capacity before upper sections can hold energy.
"""

import pytest

from custom_components.haeo.model.battery_balance_connection import BatteryBalanceConnection
from custom_components.haeo.model.network import Network


def add_economic_objective(network: Network) -> None:
    """Add infrastructure for economic objective to drive optimal solutions.

    Without priced connections, slack variables have no incentive to minimize.
    A grid with import/export pricing provides the objective function.
    """
    network.add("node", "grid_bus")
    network.add("source_sink", "grid", is_source=True, is_sink=True)
    network.add(
        "connection",
        "grid_conn",
        source="grid",
        target="grid_bus",
        price_source_target=0.30,
        price_target_source=0.10,
    )
    network.add("connection", "lower_conn", source="lower_section", target="grid_bus")
    network.add("connection", "upper_conn", source="upper_section", target="grid_bus")


# =============================================================================
# Upward Power Computation Tests
# =============================================================================


def test_balance_connection_upward_power_no_capacity_change() -> None:
    """With constant capacity, power_up = 0 since no energy needs to move up."""
    periods = [1.0] * 3
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )
    add_economic_objective(network)

    network.optimize()

    balance = network.elements["balance"]
    power_up = balance.outputs()["balance_power_up"].values

    assert power_up == pytest.approx((0.0, 0.0, 0.0), rel=1e-9, abs=1e-9)


def test_balance_connection_upward_power_with_capacity_shrinkage() -> None:
    """Capacity shrinkage forces energy to move up to maintain ordering.

    Setup:
        Lower: capacity shrinks 5→4→3→3, initial=2 kWh
        Upper: capacity=10 kWh, initial=5 kWh
        Total: 7 kWh

    Expected flow by period:
        t=1: overflow = max(0, 7-4) = 3, upper=3, lower=4
             lower 2→4 (+2), upper 5→3 (-2): power_down=2, power_up=0
        t=2: overflow = max(0, 7-3) = 4, upper=4, lower=3
             lower 4→3 (-1), upper 3→4 (+1): power_down=0, power_up=1
        t=3: overflow = max(0, 7-3) = 4, upper=4, lower=3
             lower 3→3 (0), upper 4→4 (0): no flow
    """
    periods = [1.0] * 3
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=[5.0, 4.0, 3.0, 3.0], initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 3.0, 3.0],
    )

    network.optimize()

    balance = network.elements["balance"]
    power_up = balance.outputs()["balance_power_up"].values

    assert power_up == pytest.approx((0.0, 1.0, 0.0), rel=1e-9, abs=1e-9)


def test_balance_connection_upward_power_with_capacity_growth() -> None:
    """Capacity growth allows more energy in lower, so energy flows down.

    Setup:
        Lower: capacity grows 3→4→5→5, initial=2 kWh
        Upper: capacity=10 kWh, initial=5 kWh
        Total: 7 kWh

    Expected:
        As capacity grows, lower can hold more, so energy flows DOWN to fill it
        power_up = 0 throughout (no upward flow needed)
    """
    periods = [1.0] * 3
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=[3.0, 4.0, 5.0, 5.0], initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[3.0, 4.0, 5.0, 5.0],
    )

    network.optimize()

    balance = network.elements["balance"]
    power_up = balance.outputs()["balance_power_up"].values

    assert power_up == pytest.approx((0.0, 0.0, 0.0), rel=1e-9, abs=1e-9)


def test_balance_connection_upward_power_variable_period_durations() -> None:
    """Power scales correctly with variable period durations.

    Setup:
        Periods: [0.5h, 1.0h, 2.0h]
        Lower: capacity shrinks 5→4→3→3, initial=2 kWh
        Upper: capacity=10 kWh, initial=5 kWh
        Total: 7 kWh

    Expected (same energy transitions, different power):
        Period 0 (0.5h): lower 2→4 (+2 kWh): power_down = 2/0.5 = 4 kW, power_up = 0
        Period 1 (1.0h): lower 4→3 (-1 kWh), upper 3→4 (+1 kWh): power_up = 1/1.0 = 1 kW
        Period 2 (2.0h): no change: power_up = 0
    """
    periods = [0.5, 1.0, 2.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=[5.0, 4.0, 3.0, 3.0], initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 3.0, 3.0],
    )

    network.optimize()

    balance = network.elements["balance"]
    power_up = balance.outputs()["balance_power_up"].values

    assert power_up == pytest.approx((0.0, 1.0, 0.0), rel=1e-9, abs=1e-9)


# =============================================================================
# Network Integration Tests
# =============================================================================


def test_balance_connection_network_integration() -> None:
    """BatteryBalanceConnection should integrate with Network.add() correctly."""
    periods = [1.0, 1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Add batteries first
    network.add("battery", "lower_section", capacity=[5.0, 4.0, 3.0, 3.0], initial_charge=3.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)

    # Add balance connection
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 3.0, 3.0],
    )

    # Verify the balance connection was registered correctly
    balance = network.elements["balance"]
    assert isinstance(balance, BatteryBalanceConnection)
    assert balance._upper_battery is not None
    assert balance._lower_battery is not None
    assert balance._upper_battery.name == "upper_section"
    assert balance._lower_battery.name == "lower_section"


def test_balance_connection_network_validation_missing_upper() -> None:
    """Network should raise error when balance connection upper battery is missing."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)

    with pytest.raises(TypeError, match="Upper element 'missing_battery' is not a battery"):
        network.add(
            "battery_balance_connection",
            "balance",
            upper="missing_battery",
            lower="lower_section",
            capacity_lower=[5.0, 5.0, 5.0],
        )


def test_balance_connection_network_validation_missing_lower() -> None:
    """Network should raise error when balance connection lower battery is missing."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)

    with pytest.raises(TypeError, match="Lower element 'missing_battery' is not a battery"):
        network.add(
            "battery_balance_connection",
            "balance",
            upper="upper_section",
            lower="missing_battery",
            capacity_lower=[5.0, 5.0, 5.0],
        )


# =============================================================================
# Energy Conservation Tests
# =============================================================================


def test_balance_connection_conserves_energy_isolated_system() -> None:
    """Energy should be conserved when batteries are isolated (no external source/sink)."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts with 2 kWh
    # Upper: 5 kWh capacity, starts with 0 kWh
    # Total: 2 kWh - should remain 2 kWh
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=0.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total energy should be conserved
    initial_total = lower_stored[0] + upper_stored[0]
    final_total = lower_stored[-1] + upper_stored[-1]
    assert final_total == pytest.approx(initial_total, rel=1e-6), "Total energy should be conserved"
    assert final_total == pytest.approx(2.0, rel=1e-6), "Total should be 2 kWh"


def test_balance_connection_conserves_energy_with_capacity_shrinkage() -> None:
    """Energy should be conserved even when capacity shrinks."""
    periods = [1.0]
    network = Network(name="test", periods=periods)

    # Lower: capacity shrinks from 5 to 4, starts with 2 kWh
    # Upper: 5 kWh capacity, starts with 0 kWh
    # Total: 2 kWh - should remain 2 kWh
    network.add("battery", "lower_section", capacity=[5.0, 4.0], initial_charge=2.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=0.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0],
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total energy should be conserved
    initial_total = lower_stored[0] + upper_stored[0]
    final_total = lower_stored[-1] + upper_stored[-1]
    assert final_total == pytest.approx(initial_total, rel=1e-6), "Total energy should be conserved"


def test_balance_connection_conserves_energy_both_have_charge() -> None:
    """Energy should be conserved when both sections have initial charge."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts with 2 kWh
    # Upper: 5 kWh capacity, starts with 3 kWh
    # Total: 5 kWh - should remain 5 kWh
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=3.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total energy should be conserved at all time points
    for t in range(len(lower_stored)):
        total = lower_stored[t] + upper_stored[t]
        assert total == pytest.approx(5.0, rel=1e-6), f"Total should be 5 kWh at t={t}"


# =============================================================================
# Capacity Shrinkage Constraint Tests
# =============================================================================


def test_balance_connection_downward_transfer_minimum() -> None:
    """Downward transfer should be at least equal to upward transfer."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower section capacity shrinks from 5 to 4 kWh
    # This computes power_up = 1.0 kW (bookkeeping constant)
    network.add("battery", "lower_section", capacity=[5.0, 4.0, 4.0], initial_charge=3.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 4.0],
    )

    network.optimize()

    balance = network.elements["balance"]
    outputs = balance.outputs()

    power_up = outputs["balance_power_up"].values
    power_down = outputs["balance_power_down"].values

    # Downward transfer should be >= upward transfer (constraint 1)
    for i, (up, down) in enumerate(zip(power_up, power_down, strict=True)):
        assert down >= up - 1e-9, f"Period {i}: power_down ({down}) should be >= power_up ({up})"


def test_balance_connection_shrinking_capacity_computes_upward_power() -> None:
    """Upward power is computed when stored energy exceeds new capacity.

    Setup:
        Lower: capacity=5, initial_charge=4 kWh (almost full)
        Upper: capacity=10, initial_charge=3 kWh
        capacity_lower shrinks: [5, 3, 3]
        Total: 7 kWh

    Expected:
        t=0: excess = stored[0] - capacity[1] = 4 - 3 = 1 kWh
             Lower must push 1 kWh up because it exceeds new capacity
             power_up = 1.0 kW
        t=1: excess = 3 - 3 = 0, no upward flow
             power_up = 0.0 kW
    """
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower starts almost full so capacity shrinkage forces upward flow
    network.add("source_sink", "sink", is_source=False, is_sink=True)
    network.add("battery", "lower_section", capacity=5.0, initial_charge=4.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=3.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 3.0, 3.0],
    )
    network.add("connection", "upper_to_sink", source="upper_section", target="sink")

    network.optimize()

    balance = network.elements["balance"]
    outputs = balance.outputs()

    power_up = outputs["balance_power_up"].values

    # power_up is computed from excess = stored - new_capacity
    # t=0: excess = 4 - 3 = 1, so power_up = 1.0 kW
    assert power_up[0] == pytest.approx(1.0, rel=1e-6), "Upward power should be 1.0 kW from excess"
    assert power_up[1] == pytest.approx(0.0, rel=1e-6), "No excess in period 1"


def test_balance_connection_shrinking_then_stable() -> None:
    """Power flows adapt to energy needs, not just capacity shrinkage."""
    periods = [1.0, 1.0, 1.0]
    network = Network(name="test", periods=periods)

    # capacity_lower shrinks: 5→4→3→3
    # Lower: initial_charge=2, Upper: initial_charge=5, Total=7
    # With a sink, energy can leave the system
    network.add("source_sink", "sink", is_source=False, is_sink=True)
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 3.0, 3.0],
    )
    network.add("connection", "upper_to_sink", source="upper_section", target="sink")

    network.optimize()

    balance = network.elements["balance"]
    power_up = balance.outputs()["balance_power_up"].values

    # Power flows are determined by ordering constraint, not capacity shrinkage
    # The sink allows energy to leave, so the actual flows depend on optimization
    # Key invariant: power_up[2] should be 0 when capacity is stable
    assert power_up[2] == pytest.approx(0.0, rel=1e-6), "Period 2: no capacity change, no upward flow needed"


# =============================================================================
# Power Flow Direction Tests
# =============================================================================


def test_balance_connection_net_flow_is_nonnegative() -> None:
    """Net power flow (down - up) should be >= 0 due to constraint."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # No capacity shrinkage, so power_up = 0 and power_down >= 0
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=8.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    balance = network.elements["balance"]
    outputs = balance.outputs()

    power_up = outputs["balance_power_up"].values
    power_down = outputs["balance_power_down"].values

    # Net flow = down - up (should be >= 0 for all periods)
    for i, (up, down) in enumerate(zip(power_up, power_down, strict=True)):
        net_down = down - up
        assert net_down >= -1e-6, f"Period {i}: Net flow should be >= 0 (down={down}, up={up})"


def test_balance_connection_allows_bidirectional_bookkeeping() -> None:
    """Balance connection allows energy to flow in either direction as needed."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower: initial_charge=3, capacity shrinks 5→4→4
    # Upper: initial_charge=5, total=8
    # At t=1: capacity_lower=4, overflow=max(0,8-4)=4, so upper=4, lower=4
    # From (lower=3, upper=5) to (lower=4, upper=4): 1 kWh flows down
    network.add("battery", "lower_section", capacity=5.0, initial_charge=3.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=5.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 4.0, 4.0],
    )

    network.optimize()

    balance = network.elements["balance"]
    outputs = balance.outputs()

    power_up = outputs["balance_power_up"].values
    power_down = outputs["balance_power_down"].values

    # In period 0: lower increases from 3 to 4 (+1), upper decreases from 5 to 4 (-1)
    # This means 1 kWh flows DOWN, not up
    assert power_down[0] == pytest.approx(1.0, rel=1e-6), "Downward flow to fill lower"
    assert power_up[0] == pytest.approx(0.0, rel=1e-6), "No upward flow needed"


# =============================================================================
# Edge Case Tests
# =============================================================================


def test_balance_connection_both_empty() -> None:
    """Both sections empty - system stays at zero energy."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=0.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=0.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]

    # Both should stay at zero (no energy in system)
    assert lower.outputs()["battery_energy_stored"].values[-1] == pytest.approx(0.0, rel=1e-6)
    assert upper.outputs()["battery_energy_stored"].values[-1] == pytest.approx(0.0, rel=1e-6)


def test_balance_connection_both_full() -> None:
    """Both sections full - energy is conserved."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=5.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=10.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]

    # Both should stay full (energy conserved)
    assert lower.outputs()["battery_energy_stored"].values[-1] == pytest.approx(5.0, rel=1e-6)
    assert upper.outputs()["battery_energy_stored"].values[-1] == pytest.approx(10.0, rel=1e-6)


def test_balance_connection_lower_full_upper_empty() -> None:
    """Lower full, upper empty - no transfer needed."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    network.add("battery", "lower_section", capacity=5.0, initial_charge=5.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=0.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]

    # Energy conserved: lower stays full, upper stays empty
    assert lower.outputs()["battery_energy_stored"].values[-1] == pytest.approx(5.0, rel=1e-6)
    assert upper.outputs()["battery_energy_stored"].values[-1] == pytest.approx(0.0, rel=1e-6)


def test_balance_connection_no_transfer_when_lower_full() -> None:
    """When lower is full, balance connection doesn't force extra transfer."""
    periods = [1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower full, upper has energy
    # Total = 13 kWh, should remain 13 kWh
    network.add("battery", "lower_section", capacity=5.0, initial_charge=5.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=8.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]

    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total energy conserved
    final_total = lower_stored[-1] + upper_stored[-1]
    assert final_total == pytest.approx(13.0, rel=1e-6), "Total should be 13 kWh"

    # Lower stays full
    assert lower_stored[-1] == pytest.approx(5.0, rel=1e-6), "Lower should remain at capacity"


# =============================================================================
# Ordering Constraint Tests
# =============================================================================


def test_balance_connection_ordering_lower_fills_before_upper() -> None:
    """Lower section should fill to capacity before upper gets any energy.

    This tests the ordering constraint: upper_stored <= max(0, total - capacity_lower).
    When total < capacity_lower, upper must be empty.
    When total >= capacity_lower, lower must be full.
    """
    periods = [1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts empty
    # Upper: 5 kWh capacity, starts with 3 kWh
    # Total: 3 kWh < lower capacity (5 kWh)
    # Result: All 3 kWh should end up in lower, upper should be empty
    network.add("battery", "lower_section", capacity=5.0, initial_charge=0.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=3.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total should be conserved
    assert lower_stored[-1] + upper_stored[-1] == pytest.approx(3.0, rel=1e-6)

    # All energy should be in lower (ordering enforced by constraint)
    assert lower_stored[-1] == pytest.approx(3.0, rel=1e-6), "Lower should have all 3 kWh"
    assert upper_stored[-1] == pytest.approx(0.0, rel=1e-6), "Upper should be empty"


def test_balance_connection_ordering_upper_gets_overflow() -> None:
    """Upper section can hold energy beyond what fits in lower.

    When total > capacity_lower, lower fills to capacity and upper holds the rest.
    """
    periods = [1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts with 2 kWh
    # Upper: 10 kWh capacity, starts with 6 kWh
    # Total: 8 kWh > lower capacity (5 kWh)
    # Result: Lower should be full (5 kWh), upper should have 3 kWh
    network.add("battery", "lower_section", capacity=5.0, initial_charge=2.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=6.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total should be conserved
    assert lower_stored[-1] + upper_stored[-1] == pytest.approx(8.0, rel=1e-6)

    # Lower fills to capacity, upper gets the rest
    assert lower_stored[-1] == pytest.approx(5.0, rel=1e-6), "Lower should be at capacity"
    assert upper_stored[-1] == pytest.approx(3.0, rel=1e-6), "Upper should have the overflow"


def test_balance_connection_ordering_with_shrinking_capacity() -> None:
    """Ordering constraint works with shrinking lower capacity.

    When capacity shrinks, the ordering constraint adapts.
    """
    periods = [1.0]
    network = Network(name="test", periods=periods)

    # Lower: capacity shrinks from 5 to 3 kWh, starts with 4 kWh
    # Upper: 10 kWh capacity, starts with 0 kWh
    # Total: 4 kWh > final lower capacity (3 kWh)
    # At end: lower should be full (3 kWh), upper should have 1 kWh
    network.add("battery", "lower_section", capacity=[5.0, 3.0], initial_charge=4.0)
    network.add("battery", "upper_section", capacity=10.0, initial_charge=0.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=[5.0, 3.0],
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total should be conserved
    assert lower_stored[-1] + upper_stored[-1] == pytest.approx(4.0, rel=1e-6)

    # Lower fills to its new capacity (3 kWh), upper gets the rest (1 kWh)
    assert lower_stored[-1] == pytest.approx(3.0, rel=1e-6), "Lower should be at (reduced) capacity"
    assert upper_stored[-1] == pytest.approx(1.0, rel=1e-6), "Upper should have the overflow"


def test_balance_connection_ordering_exact_fit() -> None:
    """When total exactly equals lower capacity, lower is full, upper is empty."""
    periods = [1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts with 3 kWh
    # Upper: 5 kWh capacity, starts with 2 kWh
    # Total: 5 kWh = lower capacity
    # Result: Lower should be full (5 kWh), upper should be empty (0 kWh)
    network.add("battery", "lower_section", capacity=5.0, initial_charge=3.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=2.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Total should be conserved
    assert lower_stored[-1] + upper_stored[-1] == pytest.approx(5.0, rel=1e-6)

    # Lower is exactly full, upper is empty
    assert lower_stored[-1] == pytest.approx(5.0, rel=1e-6), "Lower should be at capacity"
    assert upper_stored[-1] == pytest.approx(0.0, rel=1e-6), "Upper should be empty"


def test_balance_connection_ordering_over_multiple_periods() -> None:
    """Ordering is enforced at every energy boundary after the initial state.

    The ordering constraint applies from t=1 onwards because initial states (t=0)
    are fixed by the batteries' initial_charge values.
    """
    periods = [1.0, 1.0, 1.0]
    network = Network(name="test", periods=periods)

    # Lower: 5 kWh capacity, starts with 1 kWh
    # Upper: 5 kWh capacity, starts with 2 kWh
    # Total: 3 kWh (conserved)
    # Initial state (t=0) may violate ordering, but t=1+ should be correctly ordered
    network.add("battery", "lower_section", capacity=5.0, initial_charge=1.0)
    network.add("battery", "upper_section", capacity=5.0, initial_charge=2.0)
    network.add(
        "battery_balance_connection",
        "balance",
        upper="upper_section",
        lower="lower_section",
        capacity_lower=5.0,
    )

    network.optimize()

    lower = network.elements["lower_section"]
    upper = network.elements["upper_section"]
    lower_stored = lower.outputs()["battery_energy_stored"].values
    upper_stored = upper.outputs()["battery_energy_stored"].values

    # Check ordering at energy boundaries AFTER initial state (t=1 onwards)
    for t in range(1, len(lower_stored)):
        total = lower_stored[t] + upper_stored[t]
        capacity_lower = 5.0

        # Total should be conserved
        assert total == pytest.approx(3.0, rel=1e-6), f"Total at t={t} should be 3 kWh"

        if total <= capacity_lower:
            # All energy should be in lower
            assert upper_stored[t] == pytest.approx(0.0, rel=1e-6), f"Upper at t={t} should be empty"
        else:
            # Lower should be full
            assert lower_stored[t] == pytest.approx(capacity_lower, rel=1e-6), f"Lower at t={t} should be full"
