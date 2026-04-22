"""Element type identifiers for HAEO integration."""

from enum import StrEnum


class ElementType(StrEnum):
    """Element type identifiers for HAEO integration."""

    BATTERY = "battery"
    CONNECTION = "connection"
    GRID = "grid"
    INVERTER = "inverter"
    LOAD = "load"
    NODE = "node"
    SOLAR = "solar"
    POLICY = "policy"
