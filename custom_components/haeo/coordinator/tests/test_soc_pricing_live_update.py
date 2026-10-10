"""Regression for issue #467: live battery limit edits must reach the LP.

When a battery is configured with an undercharge partition, its ``min_charge``
floor reaches the LP only through the discharge ``soc_pricing`` segment's
``discharge_energy_threshold``. Editing ``min_charge`` while the integration is
running must update that threshold on the live model element (via the element
updater's ``TrackedParam`` writes), without requiring a full reload.
"""

from unittest.mock import MagicMock

import numpy as np

from custom_components.haeo.coordinator.network import create_network
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments.soc_pricing import SocPricingSegment
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE, NodeConfigData

BATTERY_NAME = "Test Battery"
BUS_NAME = "DC Bus"


def _battery_config(min_charge_ratio: float) -> BatteryConfigData:
    """Build a resolved battery config whose min_charge reaches the LP via soc_pricing.

    With the undercharge percentage at 0, ``lower_ratio`` is 0, so ``capacity``
    does not depend on ``min_charge``; the floor is carried solely by the
    discharge ``soc_pricing`` threshold = ``(min - lower) * capacity``.
    """
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
        power_limits={
            "max_power_source_target": np.array([5.0]),
            "max_power_target_source": np.array([5.0]),
        },
        pricing={"salvage_value": 0.0},
        efficiency={
            "efficiency_source_target": np.array([0.95]),
            "efficiency_target_source": np.array([0.95]),
        },
        partitioning={},
        undercharge={
            "percentage": np.array([0.0, 0.0]),
            "cost": np.array([0.03]),
        },
    )


async def test_min_charge_edit_updates_live_soc_pricing_threshold() -> None:
    """Editing min_charge updates the live soc_pricing discharge threshold."""
    bus: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": BUS_NAME,
        SECTION_ROLE: {CONF_IS_SOURCE: True, CONF_IS_SINK: True},
    }
    participants: dict[str, ElementConfigData] = {
        BUS_NAME: bus,
        BATTERY_NAME: _battery_config(0.2),
    }

    entry = MagicMock()
    entry.entry_id = "test_entry"
    network, updaters = await create_network(entry, periods_seconds=[3600], participants=participants)

    discharge = network.elements[f"{BATTERY_NAME}:discharge"]
    assert isinstance(discharge, Connection)
    segment = discharge.segments["soc_pricing"]
    assert isinstance(segment, SocPricingSegment)

    # min=0.2, capacity=10, lower=0 -> threshold = (0.2 - 0) * 10 = 2.0
    np.testing.assert_allclose(np.asarray(segment.discharge_energy_threshold, dtype=float), [2.0])

    # Edit min_charge to 0.5 and push it through the updater (no reload).
    updaters[BATTERY_NAME](_battery_config(0.5))

    # Live threshold must follow: (0.5 - 0) * 10 = 5.0
    np.testing.assert_allclose(np.asarray(segment.discharge_energy_threshold, dtype=float), [5.0])
