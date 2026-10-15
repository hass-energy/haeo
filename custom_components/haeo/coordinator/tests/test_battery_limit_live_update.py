"""Regression for issue #467: live battery limit edits must reach the LP.

Editing the min or max charge percentage, or the cost that holds them, while the
integration is running must update the live model battery's ``min_charge``,
``max_charge`` and ``charge_limit_cost`` through the element updater's
``TrackedParam`` writes, without requiring a full reload.
"""

from unittest.mock import MagicMock

import numpy as np
import pytest

from custom_components.haeo.coordinator.network import create_network
from custom_components.haeo.core.model.elements.battery import Battery
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE, NodeConfigData

BATTERY_NAME = "Test Battery"
BUS_NAME = "DC Bus"


def _battery_config(
    min_charge_ratio: float, max_charge_ratio: float, charge_limit_cost: float = 100.0
) -> BatteryConfigData:
    """Build a resolved battery config with the given min and max charge ratios and the cost holding them."""
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
            "max_charge_percentage": np.array([max_charge_ratio, max_charge_ratio]),
        },
        power_limits={
            "max_power_source_target": np.array([5.0]),
            "max_power_target_source": np.array([5.0]),
        },
        pricing={"salvage_value": 0.0},
        efficiency={
            "efficiency_source_target": np.array([0.95]),
            "efficiency_target_source": np.array([0.95]),
        },
        advanced={"charge_limit_cost": np.array([charge_limit_cost])},
    )


@pytest.mark.parametrize(
    ("edit", "expected_min", "expected_max", "expected_cost"),
    [
        pytest.param((0.5, 0.9, 100.0), [5.0, 5.0], [9.0, 9.0], [100.0], id="min_charge"),
        pytest.param((0.2, 0.6, 100.0), [2.0, 2.0], [6.0, 6.0], [100.0], id="max_charge"),
        pytest.param((0.2, 0.9, 40.0), [2.0, 2.0], [9.0, 9.0], [40.0], id="charge_limit_cost"),
    ],
)
async def test_charge_limit_edit_updates_live_battery(
    edit: tuple[float, float, float],
    expected_min: list[float],
    expected_max: list[float],
    expected_cost: list[float],
) -> None:
    """Editing a charge limit or its cost updates the live battery without a rebuild."""
    bus: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": BUS_NAME,
        SECTION_ROLE: {CONF_IS_SOURCE: True, CONF_IS_SINK: True},
    }
    participants: dict[str, ElementConfigData] = {
        BUS_NAME: bus,
        BATTERY_NAME: _battery_config(0.2, 0.9),
    }

    entry = MagicMock()
    entry.entry_id = "test_entry"
    network, updaters = await create_network(entry, periods_seconds=[3600], participants=participants)

    battery = network.elements[BATTERY_NAME]
    assert isinstance(battery, Battery)
    np.testing.assert_allclose(battery.charge_floor, [2.0, 2.0])
    np.testing.assert_allclose(battery.charge_ceiling, [9.0, 9.0])

    np.testing.assert_allclose(battery.charge_limit_cost, [100.0])

    updaters[BATTERY_NAME](_battery_config(*edit))

    assert network.elements[BATTERY_NAME] is battery
    np.testing.assert_allclose(battery.charge_floor, expected_min)
    np.testing.assert_allclose(battery.charge_ceiling, expected_max)
    np.testing.assert_allclose(battery.charge_limit_cost, expected_cost)
