"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final, Literal

from .battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .source_sink import SOURCE_SINK_OUTPUT_NAMES, SourceSinkOutputName

# Network-level output names (not from elements)
type NetworkOutputName = Literal[
    "optimization_cost",
    "optimization_status",
    "optimization_duration",
]

OUTPUT_NAME_OPTIMIZATION_COST: Final = "optimization_cost"
OUTPUT_NAME_OPTIMIZATION_STATUS: Final = "optimization_status"
OUTPUT_NAME_OPTIMIZATION_DURATION: Final = "optimization_duration"

NETWORK_OUTPUT_NAMES: Final[frozenset[NetworkOutputName]] = frozenset(
    [
        OUTPUT_NAME_OPTIMIZATION_COST,
        OUTPUT_NAME_OPTIMIZATION_STATUS,
        OUTPUT_NAME_OPTIMIZATION_DURATION,
    ]
)

# Combined type for all possible output names
# Note: Grid/Load/Photovoltaics outputs are now provided by adapter layer in elements/
type OutputName = BatteryOutputName | ConnectionOutputName | NetworkOutputName | SourceSinkOutputName

# Aggregated set of all output names from model and adapter elements
ALL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *CONNECTION_OUTPUT_NAMES,
        *NETWORK_OUTPUT_NAMES,
        *SOURCE_SINK_OUTPUT_NAMES,
    }
)

__all__ = [
    "ALL_OUTPUT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "NETWORK_OUTPUT_NAMES",
    "SOURCE_SINK_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "NetworkOutputName",
    "OutputName",
    "SourceSinkOutputName",
]
