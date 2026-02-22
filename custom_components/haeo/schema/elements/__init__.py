"""Element schema definitions for HAEO integration."""

from typing import Literal

from .battery import ELEMENT_TYPE as ELEMENT_TYPE_BATTERY
from .battery_section import ELEMENT_TYPE as ELEMENT_TYPE_BATTERY_SECTION
from .connection import ELEMENT_TYPE as ELEMENT_TYPE_CONNECTION
from .grid import ELEMENT_TYPE as ELEMENT_TYPE_GRID
from .inverter import ELEMENT_TYPE as ELEMENT_TYPE_INVERTER
from .load import ELEMENT_TYPE as ELEMENT_TYPE_LOAD
from .node import ELEMENT_TYPE as ELEMENT_TYPE_NODE
from .solar import ELEMENT_TYPE as ELEMENT_TYPE_SOLAR

type ElementType = Literal[
    "battery",
    "battery_section",
    "connection",
    "solar",
    "grid",
    "inverter",
    "load",
    "node",
]

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
