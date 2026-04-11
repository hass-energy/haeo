"""Policy scenario: solar export and grid import controls.

Models a home energy system with policies controlling power flow:
- Grid (import/export with time-varying pricing)
- Solar (generation with daytime peak)
- Load (constant consumption)
- Switchboard (routing node)

Policies:
- Solar -> Grid: $0.02/kWh (adds cost to solar export, discourages when grid export price < 2c)
- Grid -> Load: $0.00/kWh (allows grid to supply load, no extra cost)
- Solar -> Load: $0.00/kWh (allows solar to supply load, no extra cost)
"""

import numpy as np
import pytest

from custom_components.haeo.core.adapters.tariff_compilation import compile_policies
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.network import Network


def test_solar_export_policy_discourages_cheap_export() -> None:
    """Solar->Grid policy adds cost, discouraging export when grid price is low.

    3 periods of 1 hour:
    - Period 0: Grid export $0.01, Solar 3kW, Load 2kW.
      Solar->Grid policy $0.02. Net export value: $0.01 - $0.02 = -$0.01.
      Solar should NOT export (loses money). Excess solar curtailed.
    - Period 1: Grid export $0.05, Solar 3kW, Load 2kW.
      Net export value: $0.05 - $0.02 = $0.03. Solar SHOULD export.
    - Period 2: Grid export $0.01, Solar 0kW, Load 2kW.
      Grid imports at $0.20. No solar, no export decision.
    """
    periods = np.ones(3)

    elements: list[dict] = [
        {"element_type": "node", "name": "grid", "is_source": True, "is_sink": True},
        {"element_type": "node", "name": "solar", "is_source": True, "is_sink": False},
        {"element_type": "node", "name": "sw", "is_source": False, "is_sink": False},
        {"element_type": "node", "name": "load", "is_source": False, "is_sink": True},
        # Grid connection
        {
            "element_type": "connection",
            "name": "grid_conn",
            "source": "grid",
            "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(3, 100.0),
                    "max_power_target_source": np.full(3, 100.0),
                },
                "pricing": {
                    "segment_type": "pricing",
                    "price_source_target": np.array([0.20, 0.20, 0.20]),  # import price
                    "price_target_source": -np.array([0.01, 0.05, 0.01]),  # export revenue
                },
            },
        },
        # Solar connection (with curtailment: max is ceiling, not fixed)
        {
            "element_type": "connection",
            "name": "solar_conn",
            "source": "solar",
            "target": "sw",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.array([3.0, 3.0, 0.0]),
                    "max_power_target_source": np.zeros(3),
                },
            },
        },
        # Load connection (fixed consumption)
        {
            "element_type": "connection",
            "name": "load_conn",
            "source": "sw",
            "target": "load",
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power_source_target": np.full(3, 2.0),
                    "max_power_target_source": np.zeros(3),
                    "fixed": True,
                },
            },
        },
    ]

    policies = [
        # Solar export to grid costs $0.02/kWh extra
        {"sources": ["solar"], "destinations": ["grid"], "price_source_target": 0.02},
        # Grid and solar can both supply load (no extra cost)
        {"sources": ["grid"], "destinations": ["load"], "price_source_target": 0.00},
        {"sources": ["solar"], "destinations": ["load"], "price_source_target": 0.00},
    ]

    compiled = compile_policies(elements, policies)

    network = Network(name="policy_scenario", periods=periods)
    for elem in sorted(compiled, key=lambda e: e.get("element_type") == "connection"):
        network.add(elem)

    cost = network.optimize()
    h = network._solver

    assert isinstance(cost, float)

    grid_conn = network.elements["grid_conn"]
    solar_conn = network.elements["solar_conn"]
    load_conn = network.elements["load_conn"]

    assert isinstance(grid_conn, Connection)
    assert isinstance(solar_conn, Connection)
    assert isinstance(load_conn, Connection)

    grid_import = tuple(float(v) for v in h.vals(grid_conn.power_source_target))
    grid_export = tuple(float(v) for v in h.vals(grid_conn.power_target_source))
    solar_gen = tuple(float(v) for v in h.vals(solar_conn.power_source_target))
    load_power = tuple(float(v) for v in h.vals(load_conn.power_source_target))

    # Load is always 2 kW
    assert load_power == pytest.approx((2.0, 2.0, 2.0), abs=0.01)

    # Period 0: Solar 3kW available, export $0.01, policy $0.02. Net = -$0.01.
    # Solar should supply load (2kW free) but NOT export surplus (loses money).
    # So solar generates exactly 2 kW (just enough for load), not 3 kW.
    assert solar_gen[0] == pytest.approx(2.0, abs=0.1)  # Solar curtailed to load
    assert grid_export[0] == pytest.approx(0.0, abs=0.1)  # No export

    # Period 1: Solar 3kW, export $0.05, policy $0.02. Net = $0.03. Profitable!
    # Solar generates max 3kW: 2kW to load + 1kW exported.
    assert solar_gen[1] == pytest.approx(3.0, abs=0.1)
    assert grid_export[1] > 0.5  # Solar surplus exported

    # Period 2: No solar. Grid imports for load.
    assert solar_gen[2] == pytest.approx(0.0, abs=0.01)
    assert grid_import[2] == pytest.approx(2.0, abs=0.1)
