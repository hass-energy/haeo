"""Test battery multi-section model with soft limits."""

from pulp import LpMinimize, LpProblem, LpVariable, getSolver, lpSum
import pytest

from custom_components.haeo.model.battery import Battery
from custom_components.haeo.model.util import extract_values


def test_battery_with_overcharge_section_only() -> None:
    """Test battery with overcharge section (above preferred maximum)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        overcharge_percentage=95.0,  # Absolute maximum (outer bound)
        overcharge_cost=5.0,
    )

    # Verify two sections created: normal + overcharge
    assert len(battery.sections) == 2
    assert battery.sections[0].name == "normal"
    assert battery.sections[1].name == "overcharge"

    # Verify section boundaries
    assert battery.sections[0].lower_percentage == 10.0
    assert battery.sections[0].upper_percentage == 80.0
    assert battery.sections[1].lower_percentage == 80.0
    assert battery.sections[1].upper_percentage == 95.0

    # Verify virtual capacities
    # Normal section: (80-10)/100 * 10kWh = 7kWh
    assert battery.sections[0].virtual_capacity == pytest.approx([7.0, 7.0, 7.0])
    # Overcharge section: (95-80)/100 * 10kWh = 1.5kWh
    assert battery.sections[1].virtual_capacity == pytest.approx([1.5, 1.5, 1.5])

    # Verify costs
    assert battery.sections[1].charge_cost[0] == pytest.approx(5.0)

    # Verify energy balance constraints exist
    constraints = battery.constraints()
    assert len(constraints) > 0


def test_battery_with_undercharge_section_only() -> None:
    """Test battery with undercharge section (below preferred minimum)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=20.0,
        max_charge_percentage=90.0,
        undercharge_percentage=5.0,  # Absolute minimum (outer bound)
        undercharge_cost=3.0,
    )

    # Verify two sections created: undercharge + normal
    assert len(battery.sections) == 2
    assert battery.sections[0].name == "undercharge"
    assert battery.sections[1].name == "normal"

    # Verify section boundaries
    assert battery.sections[0].lower_percentage == 5.0
    assert battery.sections[0].upper_percentage == 20.0
    assert battery.sections[1].lower_percentage == 20.0
    assert battery.sections[1].upper_percentage == 90.0

    # Verify virtual capacities
    # Undercharge section: (20-5)/100 * 10kWh = 1.5kWh
    assert battery.sections[0].virtual_capacity == pytest.approx([1.5, 1.5, 1.5])
    # Normal section: (90-20)/100 * 10kWh = 7kWh
    assert battery.sections[1].virtual_capacity == pytest.approx([7.0, 7.0, 7.0])

    # Verify undercharge discharge cost
    assert battery.sections[0].discharge_cost[0] == pytest.approx(3.0)


def test_battery_with_all_three_sections() -> None:
    """Test battery with undercharge, normal, and overcharge sections."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=90.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Verify three sections created
    assert len(battery.sections) == 3
    assert battery.sections[0].name == "undercharge"
    assert battery.sections[1].name == "normal"
    assert battery.sections[2].name == "overcharge"

    # Verify section boundaries
    assert battery.sections[0].lower_percentage == 5.0
    assert battery.sections[0].upper_percentage == 10.0
    assert battery.sections[1].lower_percentage == 10.0
    assert battery.sections[1].upper_percentage == 90.0
    assert battery.sections[2].lower_percentage == 90.0
    assert battery.sections[2].upper_percentage == 95.0

    # Verify virtual capacities
    # Undercharge: (10-5)/100 * 10 = 0.5kWh
    assert battery.sections[0].virtual_capacity == pytest.approx([0.5, 0.5, 0.5])
    # Normal: (90-10)/100 * 10 = 8kWh
    assert battery.sections[1].virtual_capacity == pytest.approx([8.0, 8.0, 8.0])
    # Overcharge: (95-90)/100 * 10 = 0.5kWh
    assert battery.sections[2].virtual_capacity == pytest.approx([0.5, 0.5, 0.5])

    # Verify costs
    assert battery.sections[0].discharge_cost[0] == pytest.approx(2.0)
    assert battery.sections[2].charge_cost[0] == pytest.approx(4.0)


def test_battery_without_soft_limits() -> None:
    """Test battery without additional sections (normal section only)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
    )

    # Verify only one section (normal)
    assert len(battery.sections) == 1
    assert battery.sections[0].name == "normal"


def test_battery_with_time_varying_costs() -> None:
    """Test battery with time-varying over/undercharge costs."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
        undercharge_cost=[1.0, 2.0, 3.0],
        overcharge_cost=[4.0, 5.0, 6.0],
    )

    # Verify cost values broadcasted correctly per section
    assert battery.sections[0].discharge_cost == pytest.approx([1.0, 2.0, 3.0])
    assert battery.sections[2].charge_cost == pytest.approx([4.0, 5.0, 6.0])


def test_battery_section_without_cost() -> None:
    """Test battery with sections but no additional costs (should use default costs)."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        overcharge_percentage=95.0,
    )

    # Should have two sections (normal + overcharge)
    assert len(battery.sections) == 2
    # Overcharge section charge cost should default to 0
    assert battery.sections[1].charge_cost == pytest.approx([0.0, 0.0, 0.0])


def test_battery_multi_section_constraints() -> None:
    """Test that multi-section constraints are properly added."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    constraints = battery.constraints()

    # With 3 sections and n_periods=3, should have multiple constraints:
    # - Monotonicity: 2 per section per timestep (6 sections * 2 periods = 12)
    # - Stacked SOC: 2 comparisons * 2 periods = 4
    # - Power consistency: 2 periods = 2
    # Total: 12 + 4 + 2 = 18 constraints (within ENERGY_BALANCE constraint group)
    assert len(constraints) >= 18


def test_battery_multi_section_cost() -> None:
    """Test that multi-section costs are properly calculated."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Cost should be calculable
    cost = battery.cost()
    assert cost is not None
    assert len(cost) > 0


def test_battery_with_varying_capacity() -> None:
    """Test battery with time-varying capacity and multiple sections."""
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=3,
        capacity=[10.0, 12.0, 15.0],
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
        undercharge_cost=2.0,
        overcharge_cost=4.0,
    )

    # Virtual capacities should scale with capacity
    # Undercharge: (10-5)/100 * [10, 12, 15] = [0.5, 0.6, 0.75]
    assert battery.sections[0].virtual_capacity == pytest.approx([0.5, 0.6, 0.75])
    # Normal: (80-10)/100 * [10, 12, 15] = [7.0, 8.4, 10.5]
    assert battery.sections[1].virtual_capacity == pytest.approx([7.0, 8.4, 10.5])
    # Overcharge: (95-80)/100 * [10, 12, 15] = [1.5, 1.8, 2.25]
    assert battery.sections[2].virtual_capacity == pytest.approx([1.5, 1.8, 2.25])


def test_battery_initial_energy_distribution() -> None:
    """Test that initial energy is correctly distributed across sections."""
    # Initial SOC of 50% with sections [5-10-80-95]
    # Total energy = 50% * 10kWh = 5kWh
    # Section 0 (5-10%): 0.5kWh (full)
    # Section 1 (10-80%): 4.5kWh (partial fill of 7kWh capacity)
    # Section 2 (80-95%): 0kWh (empty)
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=2,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=10.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,
        overcharge_percentage=95.0,
    )

    # Extract initial energy from each section (t=0)
    section0_initial = extract_values([battery.sections[0].energy_charged[0]])[0]
    section1_initial = extract_values([battery.sections[1].energy_charged[0]])[0]
    section2_initial = extract_values([battery.sections[2].energy_charged[0]])[0]

    assert section0_initial == pytest.approx(0.5)  # Undercharge section full
    assert section1_initial == pytest.approx(4.5)  # Normal section partially filled
    assert section2_initial == pytest.approx(0.0)  # Overcharge section empty


def test_battery_parameter_validation() -> None:
    """Test that invalid parameter ordering raises ValueError."""
    # undercharge must be < min_charge
    with pytest.raises(ValueError, match=r"undercharge_percentage.*must be less than.*min_charge"):
        Battery(
            name="test",
            period=1.0,
            n_periods=2,
            capacity=10.0,
            initial_charge_percentage=50.0,
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            undercharge_percentage=15.0,  # Invalid: >= min_charge
        )

    # overcharge must be > max_charge
    with pytest.raises(ValueError, match=r"overcharge_percentage.*must be greater than.*max_charge"):
        Battery(
            name="test",
            period=1.0,
            n_periods=2,
            capacity=10.0,
            initial_charge_percentage=50.0,
            min_charge_percentage=10.0,
            max_charge_percentage=90.0,
            overcharge_percentage=85.0,  # Invalid: <= max_charge
        )

    # min must be < max
    with pytest.raises(ValueError, match=r"min_charge_percentage.*must be less than.*max_charge"):
        Battery(
            name="test",
            period=1.0,
            n_periods=2,
            capacity=10.0,
            initial_charge_percentage=50.0,
            min_charge_percentage=90.0,  # Invalid: >= max_charge
            max_charge_percentage=10.0,
        )


def test_battery_temporal_optimization() -> None:
    """Test that battery charges when future rewards make it worthwhile.

    This test demonstrates that the battery will charge during low-price periods
    and discharge during high-price periods, showing that the optimizer considers
    future value and not just immediate costs.
    """
    # Create battery that can hold enough energy for the arbitrage
    battery = Battery(
        name="test_battery",
        period=1.0,  # 1 hour periods
        n_periods=5,
        capacity=10.0,  # 10 kWh capacity
        initial_charge_percentage=50.0,  # Start at 50%
        min_charge_percentage=20.0,
        max_charge_percentage=80.0,
        max_charge_power=5.0,  # Can charge at 5 kW
        max_discharge_power=5.0,  # Can discharge at 5 kW
        efficiency=95.0,  # 95% round-trip efficiency
    )

    # Set up optimization problem
    problem = LpProblem("temporal_optimization_test", LpMinimize)

    # Add battery constraints
    for constraint in battery.constraints():
        problem += constraint

    # Create grid power variables (positive = import, negative = export)
    grid_power = [LpVariable(f"grid_power_{t}", lowBound=None) for t in range(5)]

    # Grid price pattern: cheap -> expensive -> cheap
    # This should incentivize: charge when cheap, discharge when expensive, charge again
    grid_prices = [
        0.05,  # Period 0: Very cheap (5¢/kWh) - should charge
        0.10,  # Period 1: Moderate - transition
        0.50,  # Period 2: Expensive (50¢/kWh) - should discharge
        0.10,  # Period 3: Moderate - transition
        0.05,  # Period 4: Cheap again - can charge if needed
    ]

    # Constant load that needs to be served
    load_power = [3.0, 3.0, 3.0, 3.0, 3.0]  # 3 kW constant load

    # Power balance: grid + battery_production = battery_consumption + load
    for t in range(5):
        problem += grid_power[t] == battery.power_consumption[t] - battery.power_production[t] + load_power[t]

    # Objective: minimize total cost (grid power + battery costs)
    problem += lpSum([grid_power[t] * grid_prices[t] * battery.period for t in range(5)] + list(battery.cost()))

    # Solve
    solver = getSolver("HiGHS", msg=0)
    status = problem.solve(solver)
    assert status == 1, "Optimization should succeed"

    # Extract results
    power_consumption = extract_values(battery.power_consumption)
    power_production = extract_values(battery.power_production)
    outputs = battery.outputs()
    soc = outputs["battery_state_of_charge"].values

    # Verify temporal optimization behavior:
    # Period 0 (cheap): Should charge significantly
    assert power_consumption[0] > 2.0, "Should charge when prices are cheap"
    assert power_production[0] == pytest.approx(0.0), "Should not discharge when prices are cheap"

    # Period 2 (expensive): Should discharge significantly
    assert power_production[2] > 2.0, "Should discharge when prices are expensive"
    assert power_consumption[2] == pytest.approx(0.0), "Should not charge when prices are expensive"

    # SOC should increase during cheap periods and decrease during expensive periods
    assert soc[1] > soc[0], "SOC should increase after charging in period 0"
    assert soc[2] < soc[1], "SOC should decrease when discharging in period 2"

    # The battery should not charge AND discharge in the same period
    for t in range(5):
        # With proper optimization, at most one should be non-zero
        if power_consumption[t] > 0.1:
            assert power_production[t] < 0.1, f"Should not both charge and discharge in period {t}"
        if power_production[t] > 0.1:
            assert power_consumption[t] < 0.1, f"Should not both charge and discharge in period {t}"


def test_battery_temporal_optimization_with_extended_range() -> None:
    """Test temporal optimization uses extended ranges when economically beneficial.

    This test shows that with strong price signals, the battery will use
    overcharge and undercharge sections to maximize arbitrage profits.
    """
    battery = Battery(
        name="test_battery",
        period=1.0,
        n_periods=4,
        capacity=10.0,
        initial_charge_percentage=50.0,
        min_charge_percentage=20.0,
        max_charge_percentage=80.0,
        undercharge_percentage=5.0,  # Can discharge to 5%
        overcharge_percentage=95.0,  # Can charge to 95%
        undercharge_cost=0.01,  # Small penalty for using undercharge
        overcharge_cost=0.01,  # Small penalty for using overcharge
        max_charge_power=20.0,  # High power limits
        max_discharge_power=20.0,
        efficiency=100.0,  # Perfect efficiency to simplify analysis
    )

    problem = LpProblem("extended_range_optimization_test", LpMinimize)

    for constraint in battery.constraints():
        problem += constraint

    grid_power = [LpVariable(f"grid_power_{t}", lowBound=None) for t in range(4)]

    # Extreme price differential to justify using extended ranges
    grid_prices = [
        0.01,  # Period 0: Extremely cheap - charge to overcharge range
        0.05,  # Period 1: Still cheap
        1.00,  # Period 2: Very expensive - discharge to undercharge range
        0.05,  # Period 3: Moderate
    ]

    # Large load to force significant battery usage
    load_power = [8.0, 8.0, 8.0, 8.0]  # 8 kW load

    for t in range(4):
        problem += grid_power[t] == battery.power_consumption[t] - battery.power_production[t] + load_power[t]

    # Objective: minimize total cost (grid power + battery costs)
    problem += lpSum([grid_power[t] * grid_prices[t] * battery.period for t in range(4)] + list(battery.cost()))

    solver = getSolver("HiGHS", msg=0)
    status = problem.solve(solver)
    assert status == 1, "Optimization should succeed"

    outputs = battery.outputs()
    soc = outputs["battery_state_of_charge"].values

    # With extreme price differential, battery should use extended ranges
    # Period 0: Should charge above 80% (into overcharge range)
    assert soc[1] > 80.0, "Should charge into overcharge range when prices are extremely cheap"

    # Period 2-3: Should discharge below 20% (into undercharge range)
    assert soc[3] < 20.0, "Should discharge into undercharge range when prices are extremely high"

    # Verify we actually used the extended ranges
    assert soc[1] > battery.max_charge_percentage, "Should exceed preferred maximum"
    assert soc[3] < battery.min_charge_percentage, "Should go below preferred minimum"
