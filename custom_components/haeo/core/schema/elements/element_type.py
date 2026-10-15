"""Element type identifiers for HAEO integration."""

from enum import StrEnum


class ElementType(StrEnum):
    """Element type identifiers for HAEO integration."""

    BATTERY = "battery"
    BATTERY_SECTION = "battery_section"
    BUFFER = "buffer"
    CONNECTION = "connection"
    DEFERRABLE_LOAD = "deferrable_load"
    EV = "ev"
    GRID = "grid"
    INVERTER = "inverter"
    JUNCTION = "junction"
    LOAD = "load"
    NODE = "node"
    SCHEDULABLE_LOAD = "schedulable_load"
    SOLAR = "solar"
    POLICY = "policy"
