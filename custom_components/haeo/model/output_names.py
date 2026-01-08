"""Centralized output names for all HAEO model elements.

This module aggregates output name constants from all model elements for use in tests,
translations, and other integration code that needs to reference all possible outputs.
"""

from typing import Final

from .elements.battery import BATTERY_OUTPUT_NAMES, BatteryOutputName
from .elements.battery_balance_connection import (
    BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES,
    BatteryBalanceConnectionOutputName,
)
from .elements.connection import CONNECTION_OUTPUT_NAMES, ConnectionOutputName
from .elements.node import NODE_OUTPUT_NAMES, NodeOutputName
from .elements.power_connection import POWER_CONNECTION_OUTPUT_NAMES, PowerConnectionOutputName

# Combined type for all possible output names
type ModelOutputName = (
    BatteryOutputName | PowerConnectionOutputName | NodeOutputName | BatteryBalanceConnectionOutputName
)

# Model-level output names
MODEL_OUTPUT_NAMES: Final[frozenset[str]] = frozenset(
    {
        *BATTERY_OUTPUT_NAMES,
        *BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES,
        *POWER_CONNECTION_OUTPUT_NAMES,
        *NODE_OUTPUT_NAMES,
    }
)

__all__ = [
    "BATTERY_BALANCE_CONNECTION_OUTPUT_NAMES",
    "BATTERY_OUTPUT_NAMES",
    "CONNECTION_OUTPUT_NAMES",
    "MODEL_OUTPUT_NAMES",
    "NODE_OUTPUT_NAMES",
    "POWER_CONNECTION_OUTPUT_NAMES",
    "BatteryBalanceConnectionOutputName",
    "BatteryOutputName",
    "ConnectionOutputName",
    "ModelOutputName",
    "NodeOutputName",
    "PowerConnectionOutputName",
]
