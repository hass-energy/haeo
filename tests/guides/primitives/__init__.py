"""Guide primitives for browser automation.

This package provides two layers of primitives:

1. HAPage - Low-level Home Assistant UI interactions (may change between HA versions)
2. HAEO element functions - High-level HAEO element configuration

Example usage:
    from tests.guides.primitives import GuideContext, add_battery, add_grid

    with guide_context(hass, output_dir) as ctx:
        add_integration(ctx, network_name="My System")
        add_battery(ctx, BatteryConfigSchema(...))
        add_grid(ctx, GridConfigSchema(...))
"""

from tests.guides.primitives.context import GuideContext, guide_context
from tests.guides.primitives.ha_page import HAPage
from tests.guides.primitives.haeo import (
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    add_load,
    add_node,
    add_solar,
)

__all__ = [
    # Context
    "GuideContext",
    # Low-level primitives
    "HAPage",
    # HAEO element primitives
    "add_battery",
    "add_grid",
    "add_integration",
    "add_inverter",
    "add_load",
    "add_node",
    "add_solar",
    "guide_context",
]
