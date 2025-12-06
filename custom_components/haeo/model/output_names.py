"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final, Literal

# Import element-specific output names and types
from custom_components.haeo.elements.grid import GRID_POWER_BALANCE, GRID_POWER_EXPORT, GRID_POWER_IMPORT
from custom_components.haeo.elements.load import LOAD_POWER_BALANCE, LOAD_POWER_CONSUMED
from custom_components.haeo.elements.photovoltaics import PHOTOVOLTAICS_POWER_BALANCE, PHOTOVOLTAICS_POWER_PRODUCED

from .battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .const import OUTPUT_NAME_OPTIMIZATION_COST, OUTPUT_NAME_OPTIMIZATION_DURATION, OUTPUT_NAME_OPTIMIZATION_STATUS
from .node import NODE_OUTPUT_NAMES, NodeOutputName

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
# Note: Grid/Load/Photovoltaics outputs are now provided by adapter layer in elements/
type OutputName = BatteryOutputName | NodeOutputName | ConnectionOutputName | NetworkOutputName

# Aggregated set of all output names from model and adapter elements
ALL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
        *CONNECTION_OUTPUT_NAMES,
        *NETWORK_OUTPUT_NAMES,
        # Adapter layer output names
        GRID_POWER_IMPORT,
        GRID_POWER_EXPORT,
        GRID_POWER_BALANCE,
        LOAD_POWER_CONSUMED,
        LOAD_POWER_BALANCE,
        PHOTOVOLTAICS_POWER_PRODUCED,
        PHOTOVOLTAICS_POWER_BALANCE,
    }
)

__all__ = [
    "ALL_OUTPUT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "NETWORK_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "NetworkOutputName",
    "NodeOutputName",
    "OutputName",
]
