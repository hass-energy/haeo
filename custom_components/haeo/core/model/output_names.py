"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from .elements.battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .elements.buffer import BUFFER_OUTPUT_NAMES, BufferOutputName
from .elements.connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .elements.node import NODE_OUTPUT_NAMES, NodeOutputName

# Combined type for all possible output names
type ModelOutputName = BatteryOutputName | ConnectionOutputName | NodeOutputName | BufferOutputName


__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BUFFER_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "ModelOutputName",
    "NodeOutputName",
]
