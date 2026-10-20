"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from .elements.battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .elements.buffer import BUFFER_OUTPUT_NAMES, BufferOutputName
from .elements.connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .elements.deferrable_load import DEFERRABLE_LOAD_OUTPUT_NAMES, DeferrableLoadOutputName
from .elements.node import NODE_OUTPUT_NAMES, NodeOutputName
from .elements.schedulable_load import SCHEDULABLE_LOAD_OUTPUT_NAMES, SchedulableLoadOutputName

# Combined type for all possible output names
type ModelOutputName = (
    BatteryOutputName
    | BufferOutputName
    | ConnectionOutputName
    | DeferrableLoadOutputName
    | NodeOutputName
    | SchedulableLoadOutputName
)


__all__ = [
    "BATTERY_OUTPUT_NAMES",
    "BUFFER_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "DEFERRABLE_LOAD_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "SCHEDULABLE_LOAD_OUTPUT_NAMES",
    "BatteryOutputName",
    "ConnectionOutputName",
    "DeferrableLoadOutputName",
    "ModelOutputName",
    "NodeOutputName",
    "SchedulableLoadOutputName",
]
