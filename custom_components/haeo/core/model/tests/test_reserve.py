"""Tests for reserve power system."""

from highspy import Highs
import numpy as np
import pytest

from custom_components.haeo.core.model.reserve import ReserveConfig, add_reserve_constraints


def _solve_simple_reserve(
    load: list[float],
    solar: list[float],
    battery_capacity: float,
    battery_initial: float,
    battery_efficiency: float = 0.95,
    battery_discharge_limit: float = 5.0,
) -> dict:
    """Build a minimal LP with reserve constraints and solve."""
    n = len(load)
    periods = np.array([0.5] * n)

    h = Highs()
    h.silent()

    # Battery stored energy variables (n+1 boundaries)
    stored = h.addVariables(n + 1, lb=0, ub=battery_capacity, name_prefix="stored_", out_array=True)
    # Battery charge/discharge power variables
    charge = h.addVariables(n, lb=0, ub=battery_discharge_limit, name_prefix="charge_", out_array=True)
    discharge = h.addVariables(n, lb=0, ub=battery_discharge_limit, name_prefix="discharge_", out_array=True)

    # Initial SOC
    h.addConstr(stored[0] == battery_initial)

    # SOC dynamics: stored[t+1] = stored[t] + charge[t]*η*Δt - discharge[t]*Δt/η
    for t in range(n):
        h.addConstr(
            stored[t + 1]
            == stored[t]
            + charge[t] * battery_efficiency * float(periods[t])
            - discharge[t] * float(periods[t]) * (1.0 / battery_efficiency)
        )

    # Simple objective: minimize total cost (charge costs money, discharge earns)
    # Charge from grid at $0.30/kWh, discharge value = 0
    cost = Highs.qsum(charge * 0.30 * periods)
    h.minimize(cost)

    # Add reserve constraints
    config = ReserveConfig(
        island_load_power={"load": np.array(load)},
        island_gen_power={"solar": np.array(solar)},
        battery_stored_energy={"bat": stored},
        battery_efficiency={"bat": battery_efficiency},
        battery_discharge_limit={"bat": np.full(n, battery_discharge_limit)},
        periods=periods,
    )

    result = add_reserve_constraints(h, config)

    h.run()

    sol = h.getSolution()
    reserve_vals = [sol.col_value[result.reserve_requirement[t].index] for t in range(n)]
    stored_vals = [sol.col_value[stored[t].index] for t in range(n + 1)]
    charge_vals = [sol.col_value[charge[t].index] for t in range(n)]

    return {
        "reserve": reserve_vals,
        "stored": stored_vals,
        "charge": charge_vals,
        "objective": h.getInfoValue("objective_function_value")[1],
    }


def test_reserve_basic_flat_load() -> None:
    """Flat load, no solar — reserve equals total remaining energy demand."""
    r = _solve_simple_reserve(
        load=[2.0] * 4,
        solar=[0.0] * 4,
        battery_capacity=10.0,
        battery_initial=0.0,
    )
    # Total demand = 2kW x 0.5h x 4 = 4kWh
    # At t=0, reserve should be ~4kWh (need to survive all 4 periods)
    # Battery should charge to cover the reserve
    assert r["reserve"][0] == pytest.approx(4.0, abs=0.5)
    assert r["stored"][0] == 0.0  # starts empty
    # Must charge to meet reserve
    assert sum(r["charge"]) > 0


def test_reserve_with_solar_reduces_requirement() -> None:
    """Solar generation reduces the reserve requirement."""
    r_no_solar = _solve_simple_reserve(
        load=[2.0] * 4,
        solar=[0.0] * 4,
        battery_capacity=10.0,
        battery_initial=5.0,
    )
    r_with_solar = _solve_simple_reserve(
        load=[2.0] * 4,
        solar=[1.0] * 4,  # 1kW solar offsets half the load
        battery_capacity=10.0,
        battery_initial=5.0,
    )
    # Solar should reduce the reserve requirement
    assert r_with_solar["reserve"][0] < r_no_solar["reserve"][0]


def test_reserve_exceeds_capacity() -> None:
    """Reserve can exceed battery capacity (means insufficient backup)."""
    r = _solve_simple_reserve(
        load=[10.0] * 4,
        solar=[0.0] * 4,
        battery_capacity=5.0,  # way too small
        battery_initial=5.0,
    )
    # Total demand = 10kW x 0.5h x 4 = 20kWh, capacity = 5kWh
    # Reserve requirement will exceed capacity
    assert r["reserve"][0] > 5.0


def test_reserve_with_efficiency() -> None:
    """Efficiency reduces effective stored energy."""
    r_perfect = _solve_simple_reserve(
        load=[2.0] * 4,
        solar=[0.0] * 4,
        battery_capacity=10.0,
        battery_initial=5.0,
        battery_efficiency=1.0,
    )
    r_lossy = _solve_simple_reserve(
        load=[2.0] * 4,
        solar=[0.0] * 4,
        battery_capacity=10.0,
        battery_initial=5.0,
        battery_efficiency=0.90,
    )
    # With losses, need more stored energy to meet same reserve
    # So battery charges more
    assert sum(r_lossy["charge"]) >= sum(r_perfect["charge"])


def test_reserve_decreases_over_horizon() -> None:
    """Reserve requirement decreases as we approach the end of horizon."""
    r = _solve_simple_reserve(
        load=[2.0] * 8,
        solar=[0.0] * 8,
        battery_capacity=20.0,
        battery_initial=10.0,
    )
    # Earlier periods need more reserve than later ones
    assert r["reserve"][0] > r["reserve"][-1]
    # Last period reserve should be minimal (just one period left)
    assert r["reserve"][-1] == pytest.approx(1.0, abs=0.5)  # 2kW x 0.5h


def test_reserve_solar_midday_recovery() -> None:
    """Peak drawdown occurs before solar recovery, not at end."""
    # Night load, then solar recovery midday
    r = _solve_simple_reserve(
        load=[3.0, 3.0, 3.0, 3.0, 1.0, 1.0, 1.0, 1.0],
        solar=[0.0, 0.0, 0.0, 0.0, 4.0, 4.0, 4.0, 4.0],
        battery_capacity=20.0,
        battery_initial=10.0,
    )
    # Peak drawdown is during the first 4 periods (3kWx0.5hx4 = 6kWh)
    # After that, solar exceeds load (net generation)
    # Reserve at t=0 should reflect the peak drawdown, not the end-of-horizon total
    assert r["reserve"][0] == pytest.approx(6.0, abs=1.0)
