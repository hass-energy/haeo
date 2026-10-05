"""Element type identifiers for HAEO integration."""

from enum import StrEnum


class ElementType(StrEnum):
    """Element type identifiers for HAEO integration."""

    BATTERY = "battery"
    BATTERY_SECTION = "battery_section"
    CONNECTION = "connection"
    DEFERRABLE_LOAD = "deferrable_load"
    EV = "ev"
    GRID = "grid"
    INVERTER = "inverter"
    LOAD = "load"
    NODE = "node"
    SOLAR = "solar"
    POLICY = "policy"
