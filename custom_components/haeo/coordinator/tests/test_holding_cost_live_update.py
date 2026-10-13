"""Live battery holding cost edits must reach the LP without a reload.

A holding cost's threshold is measured from the battery's min charge level, so
editing either one, or the holding cost's price or enabled switch, must update the
live holding cost element through the element updater's ``TrackedParam`` writes.
"""

from unittest.mock import MagicMock

import numpy as np

from custom_components.haeo.coordinator.network import create_network
from custom_components.haeo.core.model.elements.holding_cost import HoldingCost
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE, NodeConfigData

BATTERY_NAME = "Test Battery"
BUS_NAME = "DC Bus"


def _battery_config(*, min_charge_ratio: float, cost: float, enabled: bool) -> BatteryConfigData:
    """Build a resolved 10 kWh battery with a holding cost below 50%."""
    return BatteryConfigData(
        element_type=ElementType.BATTERY,
        name=BATTERY_NAME,
        connection=as_connection_target(BUS_NAME),
        storage={
            "capacity": np.array([10.0, 10.0]),
            "initial_charge_percentage": 0.5,
        },
        limits={
            "min_charge_percentage": np.array([min_charge_ratio, min_charge_ratio]),
            "max_charge_percentage": np.array([0.9, 0.9]),
        },
        power_limits={},
        pricing={"salvage_value": 0.0},
        efficiency={},
        holding_costs=[
            {
                "name": "Reserve",
                "enabled": enabled,
                "direction": "below",
                "threshold": np.array([0.5, 0.5]),
                "cost": np.array([cost]),
            }
        ],
    )


async def test_holding_cost_edits_update_live_element() -> None:
    """Editing the min charge level, cost, or enabled switch updates the live holding cost."""
    bus: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": BUS_NAME,
        SECTION_ROLE: {CONF_IS_SOURCE: True, CONF_IS_SINK: True},
    }
    participants: dict[str, ElementConfigData] = {
        BUS_NAME: bus,
        BATTERY_NAME: _battery_config(min_charge_ratio=0.1, cost=0.03, enabled=True),
    }

    entry = MagicMock()
    entry.entry_id = "test_entry"
    network, updaters = await create_network(entry, periods_seconds=[3600], participants=participants)

    holding_cost = network.elements[f"{BATTERY_NAME}:holding_cost:0"]
    assert isinstance(holding_cost, HoldingCost)
    # (0.5 - 0.1) * 10 = 4.0
    np.testing.assert_allclose(holding_cost.threshold, [4.0])
    np.testing.assert_allclose(holding_cost.price, [0.03])

    updaters[BATTERY_NAME](_battery_config(min_charge_ratio=0.2, cost=0.05, enabled=True))

    # (0.5 - 0.2) * 10 = 3.0
    np.testing.assert_allclose(holding_cost.threshold, [3.0])
    np.testing.assert_allclose(holding_cost.price, [0.05])

    updaters[BATTERY_NAME](_battery_config(min_charge_ratio=0.2, cost=0.05, enabled=False))

    np.testing.assert_allclose(holding_cost.price, [0.0])
