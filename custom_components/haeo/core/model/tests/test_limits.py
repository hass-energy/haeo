"""Recommended hardware limits on a home system with solar, a battery, a load and the grid.

Each case is a plan whose first period needs some flows held back and leaves
others to run on their own. Only flows the plan would pay more to raise get a
limit; one held back by a full battery, a capped export, or a higher-priority
flow is left unrestricted.
"""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements import BatteryElementConfig
from custom_components.haeo.core.model.elements.segments import SegmentSpec

type Verdict = Literal["limited", "unrestricted"]


@dataclass(frozen=True)
class LimitCase:
    """A home system's inputs, one value per period, and the verdict expected for each connection."""

    description: str
    solar: list[float]
    load: list[float]
    import_price: list[float]
    export_price: list[float]
    """What exporting a kWh earns; negative when exporting costs money."""
    expected: dict[str, Verdict]
    initial_charge: float = 5.0
    max_charge: float | None = None
    charge_limit_cost: float = 0.0
    max_charge_power: float = 5.0
    max_export_power: float = 50.0
    salvage_value: float = 0.2


def _limit(max_power: NDArray[np.float64]) -> SegmentSpec:
    return {"segment_type": "power_limit", "max_power": max_power}


def _network(case: LimitCase) -> Network:
    """Return the system wired to an AC switchboard junction, optimized."""
    n = len(case.solar)
    ones = np.ones(n)
    network = Network(name="home", periods=ones)
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": True})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "switchboard", "is_source": False, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "solar", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    battery: BatteryElementConfig = {
        "element_type": ELEMENT_TYPE_BATTERY,
        "name": "battery",
        "capacity": 10.0,
        "initial_charge": case.initial_charge,
        "salvage_value": case.salvage_value,
    }
    if case.max_charge is not None:
        battery["max_charge"] = case.max_charge
        battery["charge_limit_cost"] = case.charge_limit_cost
    network.add(battery)
    efficiency: SegmentSpec = {"segment_type": "efficiency", "efficiency": 0.95}
    connections: list[tuple[str, str, str, bool, dict[str, SegmentSpec]]] = [
        (
            "import",
            "grid",
            "switchboard",
            True,
            {
                "power_limit": _limit(50.0 * ones),
                "pricing": {"segment_type": "pricing", "price": np.asarray(case.import_price)},
            },
        ),
        (
            "export",
            "switchboard",
            "grid",
            True,
            {
                "power_limit": _limit(case.max_export_power * ones),
                "pricing": {"segment_type": "pricing", "price": -np.asarray(case.export_price)},
            },
        ),
        (
            "solar_output",
            "solar",
            "switchboard",
            False,
            {"power_limit": _limit(np.asarray(case.solar, dtype=np.float64))},
        ),
        (
            "load_supply",
            "switchboard",
            "load",
            False,
            {"power_limit": {"segment_type": "power_limit", "max_power": np.asarray(case.load), "fixed": True}},
        ),
        (
            "charge",
            "switchboard",
            "battery",
            False,
            {"power_limit": _limit(case.max_charge_power * ones), "efficiency": efficiency},
        ),
        ("discharge", "battery", "switchboard", False, {"efficiency": efficiency, "power_limit": _limit(5.0 * ones)}),
    ]
    for name, source, target, external, segments in connections:
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": name,
                "source": source,
                "target": target,
                "is_external": external,
                "tags": {0},
                "segments": segments,
            }
        )
    network.optimize()
    return network


CASES = [
    LimitCase(
        "full battery and a negative export price limit export, not solar",
        solar=[20.0, 20.0],
        load=[1.0, 1.0],
        import_price=[0.30, 0.30],
        export_price=[-0.05, -0.05],
        initial_charge=10.0,
        expected={
            "export": "limited",
            "solar_output": "unrestricted",
            "charge": "unrestricted",
            "import": "unrestricted",
            "discharge": "unrestricted",
        },
    ),
    LimitCase(
        "a battery at its max charge limits charging, not solar",
        solar=[20.0, 20.0],
        load=[1.0, 1.0],
        import_price=[0.30, 0.30],
        export_price=[-0.05, -0.05],
        initial_charge=9.0,
        max_charge=9.0,
        charge_limit_cost=1.0,
        expected={"export": "limited", "charge": "limited", "solar_output": "unrestricted"},
    ),
    LimitCase(
        "charging part of the solar now to save room limits charging, while export runs free",
        solar=[6.0, 6.0],
        load=[0.0, 0.0],
        import_price=[0.40, 0.40],
        export_price=[0.10, 0.05],
        initial_charge=4.5,
        max_charge_power=3.0,
        expected={"charge": "limited", "export": "unrestricted", "solar_output": "unrestricted"},
    ),
    LimitCase(
        "a grid that pays to import limits solar to zero",
        solar=[6.0, 6.0],
        load=[2.0, 2.0],
        import_price=[-0.05, -0.05],
        export_price=[-0.06, -0.06],
        initial_charge=10.0,
        expected={"solar_output": "limited", "import": "unrestricted"},
    ),
    LimitCase(
        "export at its cap needs no limits",
        solar=[10.0, 10.0],
        load=[1.0, 1.0],
        import_price=[0.30, 0.30],
        export_price=[0.10, 0.10],
        initial_charge=10.0,
        max_export_power=5.0,
        expected={"export": "unrestricted", "solar_output": "unrestricted", "charge": "unrestricted"},
    ),
    LimitCase(
        "rationing the battery for a pricier evening limits discharge, while import runs free",
        solar=[0.0, 0.0, 0.0],
        load=[3.0, 3.0, 3.0],
        import_price=[0.30, 0.50, 0.50],
        export_price=[0.0, 0.0, 0.0],
        initial_charge=8.0,
        salvage_value=0.0,
        expected={"discharge": "limited", "import": "unrestricted"},
    ),
]


@pytest.mark.parametrize("case", CASES, ids=[c.description for c in CASES])
def test_recommended_limits(case: LimitCase) -> None:
    """Each connection is limited to its planned power only where the plan resists more flow."""
    recommendations = _network(case).recommend_limits()

    verdicts = {
        name: "unrestricted" if recommendations[name].max_power is None else "limited" for name in case.expected
    }
    assert verdicts == case.expected
    for name, verdict in case.expected.items():
        if verdict == "limited":
            assert recommendations[name].max_power == pytest.approx(max(recommendations[name].power, 0.0))
