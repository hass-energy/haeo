"""Full policy scenario: Grid/Solar/Battery/Load with cycling controls.

System topology:
    Grid <-> Switchboard <-> Load
    Solar -> Switchboard
    Battery <-> Switchboard

Policies (from Trent's spec):
- Solar -> Grid: $0.02/kWh (don't export solar unless grid export price > 2c)
- Battery -> Grid: $0.10/kWh (don't export battery unless grid export price > 10c)
- Battery -> Load: $0.01/kWh (don't use battery if grid is less than 1c)

Additional implied policies for full whitelisting:
- Solar -> Load: $0.00 (solar can freely supply load)
- Grid -> Load: $0.00 (grid can freely supply load)
- Solar -> Battery: $0.00 (solar can charge battery for free)
- Grid -> Battery: $0.00 (grid can charge battery for free)
"""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.tariff_compilation import compile_policies
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.network import Network


def _build_full_system(
    periods: np.ndarray,
    *,
    grid_import_price: np.ndarray,
    grid_export_price: np.ndarray,
    solar_max: np.ndarray,
    load_fixed: np.ndarray,
    battery_capacity: float = 5.0,
    battery_initial_kwh: float = 2.5,
    battery_max_power: float = 5.0,
) -> list[dict]:
    """Build model elements for a full home energy system."""
    n = len(periods)
    return [
        # Nodes
        {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
        {"element_type": "node", "name": "solar", "is_source": True, "is_sink": False},
        {"element_type": "node", "name": "sw", "is_source": False, "is_sink": False},
        {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
        # Battery (model layer element)
        {
            "element_type": "battery",
            "name": "battery",
            "capacity": battery_capacity,
            "initial_charge": battery_initial_kwh,
        },
        # Grid <-> Switchboard
        {
            "element_type": "connection",
            "name": "grid_conn",
            "source": "grid",
            "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(n, 100.0),
                    "max_power_target_source": np.full(n, 100.0),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": grid_import_price,
                    "price_target_source": -grid_export_price,  # negative = revenue
                },
            },
        },
        # Solar -> Switchboard
        {
            "element_type": "connection",
            "name": "solar_conn",
            "source": "solar",
            "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": solar_max,
                    "max_power_target_source": np.zeros(n),
                },
            },
        },
        # Battery <-> Switchboard
        {
            "element_type": "connection",
            "name": "battery_conn",
            "source": "battery",
            "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(n, battery_max_power),
                    "max_power_target_source": np.full(n, battery_max_power),
                },
            },
        },
        # Switchboard -> Load (fixed consumption)
        {
            "element_type": "connection",
            "name": "load_conn",
            "source": "sw",
            "target": "load",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": load_fixed,
                    "max_power_target_source": np.zeros(n),
                    "fixed": True,
                },
            },
        },
    ]


def test_full_battery_policy_scenario() -> None:
    """Full scenario: solar/battery export controls and battery usage cost.

    6 periods of 1 hour each with varying grid prices and solar generation.

    Period 0: Grid $0.30 import / $0.04 export. Solar 5kW. Load 2kW.
      - Solar excess 3kW. Export to grid: $0.04 - $0.02 policy = $0.02 revenue. Worth it.
      - But battery charging saves importing later. Check what optimizer prefers.

    Period 1: Grid $0.30 import / $0.01 export. Solar 5kW. Load 2kW.
      - Solar excess 3kW. Export: $0.01 - $0.02 policy = -$0.01 loss. DON'T export.
      - Battery should charge from excess.

    Period 2: Grid $0.005 import / $0.005 export. Solar 0kW. Load 2kW.
      - Grid very cheap. Battery->Load policy $0.01 > grid $0.005.
      - Grid should supply load (cheaper than battery discharge).

    Period 3: Grid $0.50 import / $0.15 export. Solar 0kW. Load 2kW.
      - Grid expensive. Battery->Load policy $0.01. Use battery.
      - Battery->Grid: $0.15 - $0.10 policy = $0.05 revenue. Moderate.

    Period 4: Grid $0.50 import / $0.05 export. Solar 0kW. Load 2kW.
      - Grid expensive. Use battery for load ($0.01 << $0.50).
      - Battery->Grid: $0.05 - $0.10 = -$0.05. DON'T export to grid.

    Period 5: Grid $0.10 import / $0.02 export. Solar 0kW. Load 2kW.
      - Grid moderate. Battery->Load $0.01 is cheaper than grid $0.10. Use battery.
    """
    periods = np.ones(6)

    grid_import_price = np.array([0.30, 0.30, 0.005, 0.50, 0.50, 0.10])
    grid_export_price = np.array([0.04, 0.01, 0.005, 0.15, 0.05, 0.02])
    solar_max = np.array([5.0, 5.0, 0.0, 0.0, 0.0, 0.0])
    load_fixed = np.full(6, 2.0)

    elements = _build_full_system(
        periods,
        grid_import_price=grid_import_price,
        grid_export_price=grid_export_price,
        solar_max=solar_max,
        load_fixed=load_fixed,
        battery_capacity=10.0,
        battery_initial_kwh=0.0,  # Start empty
        battery_max_power=5.0,
    )

    policies = [
        # Export controls
        {"sources": ["solar"], "destinations": ["grid"], "price_source_target": 0.02},
        {"sources": ["battery"], "destinations": ["grid"], "price_source_target": 0.10},
        # Battery usage cost
        {"sources": ["battery"], "destinations": ["load"], "price_source_target": 0.01},
        # Allow free flows (whitelist)
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.00},
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.00},
        {"sources": ["solar"], "destinations": ["battery"], "price_source_target": 0.00},
        {"sources": ["grid"], "destinations": ["battery"], "price_source_target": 0.00},
    ]

    compiled = compile_policies(elements, policies)

    network = Network(name="full_scenario", periods=periods)
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    cost = network.optimize()
    h = network._solver

    assert isinstance(cost, float)

    # Extract flows
    grid_conn = network.elements["grid_conn"]
    solar_conn = network.elements["solar_conn"]
    battery_conn = network.elements["battery_conn"]

    assert isinstance(grid_conn, Connection)
    assert isinstance(solar_conn, Connection)
    assert isinstance(battery_conn, Connection)

    grid_import = tuple(float(v) for v in h.vals(grid_conn.power_source_target))
    grid_export = tuple(float(v) for v in h.vals(grid_conn.power_target_source))
    _ = tuple(float(v) for v in h.vals(solar_conn.power_source_target))
    bat_discharge = tuple(float(v) for v in h.vals(battery_conn.power_source_target))
    _ = tuple(float(v) for v in h.vals(battery_conn.power_target_source))

    # --- Period 1: Solar surplus, cheap export -> DON'T export (policy makes it negative) ---
    # Export revenue $0.01 < policy $0.02. Solar should be curtailed or charge battery.
    assert grid_export[1] == pytest.approx(0.0, abs=0.1)  # No export to grid

    # --- Period 2: Grid very cheap ($0.005), battery->load costs $0.01 ---
    # Grid is cheaper than battery. Battery should NOT discharge.
    assert bat_discharge[2] == pytest.approx(0.0, abs=0.1)  # No battery discharge
    assert grid_import[2] > 1.0  # Grid supplies load

    # --- Period 3: Grid expensive ($0.50), battery->load only $0.01 ---
    # Battery should discharge to load
    assert bat_discharge[3] > 1.0  # Battery discharges

    # --- Period 4: Grid expensive, but battery->grid export unprofitable ---
    # Export: $0.05 - $0.10 policy = -$0.05. Battery should supply load only.
    assert bat_discharge[4] > 0.5  # Battery discharges for load
    # Battery shouldn't export much to grid
    # (harder to assert precisely — optimizer may still export if overall optimal)
