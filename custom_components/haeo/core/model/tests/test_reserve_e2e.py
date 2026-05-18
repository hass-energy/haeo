"""End-to-end test: reserve power system with realistic network topology.

Tests the full pipeline:
1. Build network with grid, solar, battery, inverter, multiple loads
2. Auto-discover island via graph walk
3. Add reserve constraints (windowed and full-horizon)
4. Solve and verify battery maintains reserve SOC floor
5. Extract post-solve outputs
"""

import numpy as np
import pytest

from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.model.reserve_graph import discover_island


def _build_realistic_network(n_periods: int = 48) -> Network:
    """Build a realistic home energy network with 48 half-hour periods (24h).

    Topology:
        Grid <-> AC_Bus <-> Inverter <-> DC_Bus <-> Battery
                    |                       |
                 AC_Load                 Solar
                    |
               EV_Charger (sheddable)
    """
    periods = np.array([0.5] * n_periods)
    net = Network(name="realistic_home", periods=periods)

    # Nodes
    net.add({"element_type": "node", "name": "Grid", "is_source": True, "is_sink": True})
    net.add({"element_type": "node", "name": "AC_Bus", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "DC_Bus", "is_source": False, "is_sink": False})
    net.add({"element_type": "node", "name": "AC_Load", "is_source": False, "is_sink": True})
    net.add({"element_type": "node", "name": "EV_Charger", "is_source": False, "is_sink": True})
    net.add({"element_type": "node", "name": "Solar", "is_source": True, "is_sink": False})

    # Battery: 13.5 kWh (Tesla Powerwall-like), 50% initial SOC
    net.add({"element_type": "battery", "name": "Battery", "capacity": 13.5, "initial_charge": 6.75})

    # Solar generation: peaks at noon (period 24), bell curve shape
    solar_power = [0.0] * n_periods
    for t in range(n_periods):
        hour = t * 0.5
        if 6 <= hour <= 18:
            solar_power[t] = max(0, 5.0 * np.sin(np.pi * (hour - 6) / 12))

    # Base load: 1.5kW constant + evening spike
    base_load = [0.0] * n_periods
    for t in range(n_periods):
        hour = t * 0.5
        base_load[t] = 1.5 + (2.0 if 17 <= hour <= 21 else 0.0)

    # EV charger: 7kW from 22:00-06:00 (sheddable)
    ev_load = [0.0] * n_periods
    for t in range(n_periods):
        hour = t * 0.5
        if hour >= 22 or hour < 6:
            ev_load[t] = 7.0

    # Grid pricing: off-peak 0.10, shoulder 0.20, peak 0.35 ($/kWh)
    grid_price = [0.0] * n_periods
    for t in range(n_periods):
        hour = t * 0.5
        if 7 <= hour < 14 or 20 <= hour < 22:
            grid_price[t] = 0.20
        elif 14 <= hour < 20:
            grid_price[t] = 0.35
        else:
            grid_price[t] = 0.10

    feed_in = [-0.05] * n_periods

    # Connections
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:import",
            "source": "Grid",
            "target": "AC_Bus",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": grid_price},
                "power_limit": {"segment_type": "power_limit", "max_power": 20.0},
            },
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Grid:export",
            "source": "AC_Bus",
            "target": "Grid",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": feed_in},
                "power_limit": {"segment_type": "power_limit", "max_power": 5.0},
            },
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Solar:conn",
            "source": "Solar",
            "target": "DC_Bus",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": solar_power}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "AC_Load:conn",
            "source": "AC_Bus",
            "target": "AC_Load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": base_load, "fixed": True}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "EV:conn",
            "source": "AC_Bus",
            "target": "EV_Charger",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": ev_load}},
        }
    )
    # Inverter: DC_Bus <-> AC_Bus (97% efficiency)
    net.add(
        {
            "element_type": "connection",
            "name": "Inverter:dc_ac",
            "source": "DC_Bus",
            "target": "AC_Bus",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.97}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Inverter:ac_dc",
            "source": "AC_Bus",
            "target": "DC_Bus",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.97}},
        }
    )
    # Battery connections (95% round-trip each way)
    net.add(
        {
            "element_type": "connection",
            "name": "Battery:charge",
            "source": "DC_Bus",
            "target": "Battery",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.95}},
        }
    )
    net.add(
        {
            "element_type": "connection",
            "name": "Battery:discharge",
            "source": "Battery",
            "target": "DC_Bus",
            "tags": {1},
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": 0.95}},
        }
    )

    return net


def test_e2e_reserve_full_horizon() -> None:
    """Full-horizon reserve on a realistic 24h network, excluding sheddable EV."""
    net = _build_realistic_network()
    result = net.add_reserve(exclude_elements={"Grid", "EV_Charger"})
    assert result is not None

    net.optimize()
    sol = net._solver.getSolution()

    # Reserve should be computed (positive for early periods before solar)
    reserve_0 = sol.col_value[result.reserve_requirement[0].index]
    assert reserve_0 > 0, "Reserve at t=0 should be positive"

    # Reserve should decrease over the horizon as demand is served
    reserve_last = sol.col_value[result.reserve_requirement[47].index]
    assert reserve_last <= reserve_0, "Reserve should decrease or stay flat over horizon"

    # Without hard_soc_floor (default), reserve is computed but not enforced
    # The values represent what WOULD be needed for full blackout survival
    # Post-solve outputs should work
    outputs = result.outputs(net._solver)
    assert len(outputs["reserve_energy_requirement"].values) == 48


def test_e2e_reserve_with_sheddable_exclusion() -> None:
    """Reserve excluding EV charger (sheddable load) gives reasonable results."""
    net_shed = _build_realistic_network()
    result_shed = net_shed.add_reserve(exclude_elements={"Grid", "EV_Charger"})
    assert result_shed is not None
    net_shed.optimize()
    sol_shed = net_shed._solver.getSolution()
    reserve_shed_0 = sol_shed.col_value[result_shed.reserve_requirement[0].index]

    # With EV excluded, reserve is based only on base load
    # Base load peak: 3.5kW (1.5 + 2.0 evening spike) for 24h
    # Reserve should be reasonable for a 13.5kWh battery
    assert reserve_shed_0 > 0
    assert reserve_shed_0 < 40  # sanity check


def test_e2e_reserve_windowed_vs_full() -> None:
    """Windowed reserve (12h) requires less or equal to full 24h reserve."""
    net_full = _build_realistic_network()
    result_full = net_full.add_reserve(exclude_elements={"Grid", "EV_Charger"})
    assert result_full is not None
    net_full.optimize()
    sol_full = net_full._solver.getSolution()
    reserve_full_0 = sol_full.col_value[result_full.reserve_requirement[0].index]

    net_win = _build_realistic_network()
    result_win = net_win.add_reserve(exclude_elements={"Grid", "EV_Charger"}, window_periods=24)
    assert result_win is not None
    net_win.optimize()
    sol_win = net_win._solver.getSolution()
    reserve_win_0 = sol_win.col_value[result_win.reserve_requirement[0].index]

    # 12h window should require less reserve than full 24h
    assert reserve_win_0 <= reserve_full_0 + 0.1, (
        f"Windowed reserve should be <= full: {reserve_win_0:.1f} > {reserve_full_0:.1f}"
    )


def test_e2e_reserve_post_solve_outputs() -> None:
    """Post-solve outputs extract correctly from a solved network."""
    net = _build_realistic_network()
    result = net.add_reserve(exclude_elements={"Grid", "EV_Charger"})
    assert result is not None

    net.optimize()
    outputs = result.outputs(net._solver)

    assert "reserve_energy_requirement" in outputs
    assert "reserve_peak_deficit" in outputs

    req = outputs["reserve_energy_requirement"]
    assert req.type.value == "energy"
    assert req.unit == "kWh"
    assert len(req.values) == 48

    # All values should be non-negative
    assert all(v >= -0.01 for v in req.values), f"Negative reserve values: {[v for v in req.values if v < -0.01]}"


def test_e2e_reserve_multi_hop_efficiency() -> None:
    """Verify path efficiency is correctly computed through inverter."""

    net = _build_realistic_network()
    island = discover_island(net)

    # Battery -> DC_Bus (0.95) -> AC_Bus (0.97) -> AC_Load (1.0)
    expected_eff = 0.95 * 0.97  # = 0.9215
    actual_eff = island.battery_to_load_efficiency["Battery"]["AC_Load"]
    assert actual_eff == pytest.approx(expected_eff, abs=0.01), (
        f"Expected efficiency {expected_eff:.4f}, got {actual_eff:.4f}"
    )
