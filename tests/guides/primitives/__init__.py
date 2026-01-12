"""Guide primitives for browser automation.

This package provides two layers of primitives:

1. HAPage - Low-level Home Assistant UI interactions (may change between HA versions)
2. HAEO element functions - High-level HAEO element configuration

Screenshots are automatically collected using ScreenshotContext with hierarchical naming.

Example usage:
    from tests.guides.primitives import HAPage, screenshot_context
    from tests.guides.primitives.haeo import add_integration, add_battery

    with screenshot_context(output_dir) as ctx:
        add_integration(page, network_name="My System")
        add_battery(page, name="Battery", connection="Inverter", ...)
        # ctx.screenshots contains OrderedDict of all captured images
"""

from tests.guides.primitives.ha_page import HAPage
from tests.guides.primitives.haeo import (
    Entity,
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    add_load,
    add_node,
    add_solar,
    login,
    verify_setup,
)
from tests.guides.primitives.capture import (
    ScreenshotContext,
    guide_step,
    screenshot_context,
)

__all__ = [
    # Screenshot context
    "ScreenshotContext",
    "guide_step",
    "screenshot_context",
    # Low-level primitives
    "HAPage",
    # Entity type
    "Entity",
    # HAEO element primitives
    "add_battery",
    "add_grid",
    "add_integration",
    "add_inverter",
    "add_load",
    "add_node",
    "add_solar",
    "login",
    "verify_setup",
]
