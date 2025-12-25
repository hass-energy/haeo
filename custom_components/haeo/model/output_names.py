"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final

from .battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .connection import CONNECTION_OUTPUT_NAMES as BASE_CONNECTION_OUTPUT_NAMES
from .connection import ConnectionOutputName as BaseConnectionOutputName
from .node import NODE_OUTPUT_NAMES, NodeOutputName
from .power_connection import POWER_CONNECTION_OUTPUT_NAMES, PowerConnectionOutputName

# Combined type for all possible output names
type ModelOutputName = BatteryOutputName | PowerConnectionOutputName | NodeOutputName

# Model-level output names
MODEL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *POWER_CONNECTION_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
    }
)

__all__ = [
    "BASE_CONNECTION_OUTPUT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "MODEL_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "BaseConnectionOutputName",
    "BatteryOutputName",
    "ModelOutputName",
    "NodeOutputName",
    "PowerConnectionOutputName",
]
