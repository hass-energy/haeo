"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final

from .battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .node import NODE_OUTPUT_NAMES, NodeOutputName

# Combined type for all possible output names
type ModelOutputName = BatteryOutputName | ConnectionOutputName | NodeOutputName

# Model-level output names
MODEL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *CONNECTION_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
    }
)

__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "MODEL_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "ModelOutputName",
    "NodeOutputName",
]
