"""Power balance shadow prices of elements that produce or consume power.

Each element publishes one energy balance dual per period. With tagged
connections, the per-tag routing rows sit in a separate constraint, so their
duals (which carry the opposite sign for production) never reach the output.
"""

import numpy as np
import pytest

from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData

N_PERIODS = 3
GRID_PRICE = 0.30
LOAD_POWER = 2.0


def _switchboard_network(tags: set[int]) -> Network:
    """Return a grid feeding a switchboard junction at a flat price, with a fixed load on the switchboard."""
    network = Network(name="test", periods=np.ones(N_PERIODS))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "switchboard", "is_source": False, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "grid_import",
            "source": "grid",
            "target": "switchboard",
            "tags": tags,
            "segments": {"pricing": {"segment_type": "pricing", "price": np.full(N_PERIODS, GRID_PRICE)}},
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "load_supply",
            "source": "switchboard",
            "target": "load",
            "tags": tags,
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": np.full(N_PERIODS, LOAD_POWER),
                    "fixed": True,
                }
            },
        }
    )
    return network


def _power_balance(network: Network, name: str) -> OutputData:
    output = network.elements[name].outputs()[ELEMENT_POWER_BALANCE]
    assert isinstance(output, OutputData)
    return output


@pytest.mark.parametrize(
    ("battery_tags", "connection_tags"),
    [
        (None, {0}),
        ({1}, {0, 1}),
    ],
    ids=["single-tag", "policied-battery"],
)
def test_battery_balance_dual_is_switchboard_price_through_efficiency(
    battery_tags: set[int] | None, connection_tags: set[int]
) -> None:
    """A battery discharging through a lossy connection values its energy at the switchboard price times efficiency.

    The battery holds less energy than the load needs, so every stored kWh
    displaces grid imports: withdrawing one more kWh at the battery delivers
    ``efficiency`` fewer kWh to the switchboard, costing ``price * efficiency``.
    """
    efficiency = 0.98
    network = _switchboard_network(connection_tags)
    network.add(
        {
            "element_type": ELEMENT_TYPE_BATTERY,
            "name": "battery",
            "capacity": 10.0,
            "initial_charge": 2.0,
            "outbound_tags": battery_tags,
            "inbound_tags": battery_tags,
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "battery_discharge",
            "source": "battery",
            "target": "switchboard",
            "tags": connection_tags,
            "segments": {"efficiency": {"segment_type": "efficiency", "efficiency": np.full(N_PERIODS, efficiency)}},
        }
    )

    network.optimize()

    switchboard = _power_balance(network, "switchboard").values
    battery = _power_balance(network, "battery").values
    assert switchboard == pytest.approx((GRID_PRICE,) * N_PERIODS, abs=1e-3)
    assert battery == pytest.approx((GRID_PRICE * efficiency,) * N_PERIODS, abs=1e-3)


def test_unused_source_balance_dual_lies_between_its_cost_gap_and_zero() -> None:
    """A source priced above the switchboard publishes one non-positive dual per period.

    Producing nothing, the source's balance dual may be anywhere in
    ``[switchboard price - connection price, 0]``: one more kWh withdrawn at the
    source could come from its own free production.
    """
    generator_price = 0.50
    network = _switchboard_network({0})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "generator", "is_source": True, "is_sink": False})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "generator_supply",
            "source": "generator",
            "target": "switchboard",
            "tags": {0},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.full(N_PERIODS, generator_price)}},
        }
    )

    network.optimize()

    generator = _power_balance(network, "generator").values
    assert len(generator) == N_PERIODS
    for value in generator:
        assert GRID_PRICE - generator_price - 1e-3 <= value <= 1e-3
