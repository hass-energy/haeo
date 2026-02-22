"""Element schema definitions for HAEO integration."""

from enum import StrEnum


class ElementType(StrEnum):
    """Element type identifiers for all HAEO element types."""

    BATTERY = "battery"
    BATTERY_SECTION = "battery_section"
    CONNECTION = "connection"
    GRID = "grid"
    INVERTER = "inverter"
    LOAD = "load"
    NODE = "node"
    SOLAR = "solar"
