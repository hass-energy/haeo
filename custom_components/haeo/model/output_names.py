"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final, Literal

# Import element-specific output names and types
from .battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .const import OUTPUT_NAME_OPTIMIZATION_COST, OUTPUT_NAME_OPTIMIZATION_DURATION, OUTPUT_NAME_OPTIMIZATION_STATUS
from .grid import GRID_OUTPUT_NAMES, GridOutputName
from .load import LOAD_OUTPUT_NAMES, LoadOutputName
from .node import NODE_OUTPUT_NAMES, NodeOutputName
from .photovoltaics import PHOTOVOLTAICS_OUTPUT_NAMES, PhotovoltaicsOutputName

# Network-level output names (not from elements)
type NetworkOutputName = Literal[
    "optimization_cost",
    "optimization_status",
    "optimization_duration",
]

NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    [
        OUTPUT_NAME_OPTIMIZATION_COST,
        OUTPUT_NAME_OPTIMIZATION_STATUS,
        OUTPUT_NAME_OPTIMIZATION_DURATION,
    ]
)

# Combined type for all possible output names
type OutputName = (
    BatteryOutputName
    | GridOutputName
    | PhotovoltaicsOutputName
    | LoadOutputName
    | NodeOutputName
    | ConnectionOutputName
    | NetworkOutputName
)

# Aggregated set of all output names from all elements
ALL_OUTPUT_NAMES: Final[frozenset[OutputName]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *GRID_OUTPUT_NAMES,
        *PHOTOVOLTAICS_OUTPUT_NAMES,
        *LOAD_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
        *CONNECTION_OUTPUT_NAMES,
        *NETWORK_OUTPUT_NAMES,
    }
)

__all__ = [
    "ALL_OUTPUT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "GRID_OUTPUT_NAMES",
    "LOAD_OUTPUT_NAMES",
    "NETWORK_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "PHOTOVOLTAICS_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "GridOutputName",
    "LoadOutputName",
    "NetworkOutputName",
    "NodeOutputName",
    "OutputName",
    "PhotovoltaicsOutputName",
]
