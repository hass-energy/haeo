"""Regression for issue #467: live battery limit edits must reach the LP.

Editing the min or max charge percentage while the integration is running must
update the live model battery's ``min_charge`` and ``max_charge`` through the
element updater's ``TrackedParam`` writes, without requiring a full reload.
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


def _battery_config(min_charge_ratio: float, max_charge_ratio: float) -> BatteryConfigData:
    """Build a resolved battery config with the given min and max charge ratios."""
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
    )


@pytest.mark.parametrize(
    ("ratios", "expected_min", "expected_max"),
    [
        pytest.param((0.5, 0.9), [5.0, 5.0], [9.0, 9.0], id="min_charge"),
        pytest.param((0.2, 0.6), [2.0, 2.0], [6.0, 6.0], id="max_charge"),
    ],
)
async def test_charge_limit_edit_updates_live_battery(
    ratios: tuple[float, float],
    expected_min: list[float],
    expected_max: list[float],
) -> None:
    """Editing a charge limit updates the live battery's min and max charge without a rebuild."""
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

    updaters[BATTERY_NAME](_battery_config(*ratios))

    assert network.elements[BATTERY_NAME] is battery
    np.testing.assert_allclose(battery.charge_floor, expected_min)
    np.testing.assert_allclose(battery.charge_ceiling, expected_max)
