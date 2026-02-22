"""Element schema definitions for HAEO integration."""

from enum import StrEnum


class ElementType(StrEnum):
    """Element type identifiers for HAEO integration."""

    BATTERY = "battery"
    BATTERY_SECTION = "battery_section"
    CONNECTION = "connection"
    GRID = "grid"
    INVERTER = "inverter"
    LOAD = "load"
    NODE = "node"
    SOLAR = "solar"


ELEMENT_TYPE_BATTERY = ElementType.BATTERY
ELEMENT_TYPE_BATTERY_SECTION = ElementType.BATTERY_SECTION
ELEMENT_TYPE_CONNECTION = ElementType.CONNECTION
ELEMENT_TYPE_GRID = ElementType.GRID
ELEMENT_TYPE_INVERTER = ElementType.INVERTER
ELEMENT_TYPE_LOAD = ElementType.LOAD
ELEMENT_TYPE_NODE = ElementType.NODE
ELEMENT_TYPE_SOLAR = ElementType.SOLAR

__all__ = [
    "ELEMENT_TYPE_BATTERY",
    "ELEMENT_TYPE_BATTERY_SECTION",
    "ELEMENT_TYPE_CONNECTION",
    "ELEMENT_TYPE_GRID",
    "ELEMENT_TYPE_INVERTER",
    "ELEMENT_TYPE_LOAD",
    "ELEMENT_TYPE_NODE",
    "ELEMENT_TYPE_SOLAR",
    "ElementType",
]
