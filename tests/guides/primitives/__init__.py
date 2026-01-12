"""Guide primitives for browser automation.

This package provides two layers of primitives:

1. HAPage - Low-level Home Assistant UI interactions (may change between HA versions)
2. HAEO element functions - High-level HAEO element configuration

Example usage:
    from tests.guides.primitives import GuideContext, BatteryConfig, GridConfig

    with guide_context(hass, output_dir) as ctx:
        add_integration(ctx, network_name="My System")
        add_battery(ctx, BatteryConfig(name="Battery", ...))
        add_grid(ctx, GridConfig(name="Grid", ...))
"""

from tests.guides.primitives.context import GuideContext, guide_context
from tests.guides.primitives.ha_page import HAPage
from tests.guides.primitives.haeo import (
    BatteryConfig,
    Entity,
    GridConfig,
    InverterConfig,
    LoadConfig,
    NodeConfig,
    SolarConfig,
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

__all__ = [
    # Context
    "GuideContext",
    "guide_context",
    # Low-level primitives
    "HAPage",
    # Config types
    "BatteryConfig",
    "Entity",
    "GridConfig",
    "InverterConfig",
    "LoadConfig",
    "NodeConfig",
    "SolarConfig",
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
